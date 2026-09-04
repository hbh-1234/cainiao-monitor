# -*- coding: utf-8 -*-
"""登录窗口 —— Surfboard 风格 · 服务商选择架构
数据服务商（四选一）：
  1. 菜鸟账号：手机号 + 短信验证码授权（内嵌浏览器，懒加载）或粘贴 Cookie
  2. 快递鸟 API：EBusinessID + AppKey（即时查询接口）
  3. 快递100 API：customer + key（企业轮询接口；也可用免费公开查询）
  4. 模拟模式：无需任何账号，演示完整流程
"""
from __future__ import annotations

import os
import random
import re
import webbrowser

from PySide6.QtCore import QUrl, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QRadialGradient
from PySide6.QtWidgets import (QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QStackedLayout,
                               QTextEdit, QVBoxLayout, QWidget)

from ..api.http_client import ApiError, LoginRequired, NetworkError, build_session
from ..api.wuliu import WULIU_LIST, fetch_packages
from ..config import Config, app_data_dir
from ..constants import (COLOR_ACCENT_SOFT, COLOR_BG_BOTTOM, COLOR_BG_TOP,
                         COLOR_CHIP_CYAN_BG, COLOR_CHIP_CYAN_FG, COLOR_ERR,
                         COLOR_TEXT, COLOR_TEXT_SUB)
from .icons import make_app_icon

# 是否可用内嵌浏览器（未安装 WebEngine 或设置了 CAINIAO_NO_WEBENGINE 时为 False，自动降级）
try:
    if os.environ.get("CAINIAO_NO_WEBENGINE") == "1":
        raise ImportError("webengine disabled by env")
    from PySide6.QtWebEngineWidgets import QWebEnginePage, QWebEngineView
    from PySide6.QtWebEngineCore import QWebEngineProfile
    HAVE_WEBENGINE = True
except Exception:
    HAVE_WEBENGINE = False


# ---------------------------------------------------------------
# Cookie 校验线程（requests 验证登录态并抓取列表）
# ---------------------------------------------------------------
class VerifyWorker(QThread):
    ok = Signal(object)     # cookies dict
    fail = Signal(str)      # 失败原因

    def __init__(self, cookies: dict, parent=None):
        super().__init__(parent)
        self.cookies = cookies

    def run(self):
        session = build_session(self.cookies)
        try:
            pkgs = fetch_packages(session)
            self.ok.emit(self.cookies)
        except LoginRequired:
            self.fail.emit("登录态无效或已过期，请重新登录")
        except NetworkError as e:
            self.fail.emit(str(e))
        except ApiError as e:
            # 已登录但页面解析失败：仍然放行，主界面会给出提示
            self.ok.emit(self.cookies)
        except Exception as e:
            self.fail.emit(f"未知错误：{e}")


# ---------------------------------------------------------------
# 模拟登录对话框（无需真实手机号：演示完整登录→监控→通知流程）
# ---------------------------------------------------------------
class SimulationDialog(QDialog):
    confirmed = Signal(str)   # 手机号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("模拟模式")
        self.setFixedSize(420, 380)
        self.setStyleSheet(f"QDialog {{ background: {COLOR_BG_TOP}; }}")

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 22)
        root.setSpacing(14)

        title = QLabel("模拟模式（无需真实手机号）")
        f = QFont("Segoe UI", 17)
        f.setBold(True)
        title.setFont(f)
        
        root.addWidget(title)

        tip = QLabel("模拟「手机号 + 短信验证码」授权流程，并生成演示包裹数据。\n"
                     "不会连接菜鸟/淘宝服务器，适合先体验界面与通知功能。")
        tip.setWordWrap(True)
        tip.setObjectName("TxtSub")
        tip.setStyleSheet("font-size: 13px;")
        root.addWidget(tip)

        card = QFrame()
        card.setObjectName("SurfCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 16, 18, 16)
        cl.setSpacing(10)

        cl.addWidget(QLabel("手机号"))
        self.phone_edit = QLineEdit("13800138000")
        self.phone_edit.setMaxLength(11)
        cl.addWidget(self.phone_edit)

        row = QHBoxLayout()
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("短信验证码")
        self.code_edit.setMaxLength(6)
        row.addWidget(self.code_edit, 1)
        send_btn = QPushButton("获取验证码")
        send_btn.setObjectName("SurfTonal")
        send_btn.clicked.connect(self._send_code)
        row.addWidget(send_btn)
        cl.addLayout(row)

        self.code_hint = QLabel("")
        self.code_hint.setObjectName("TxtAccent")
        self.code_hint.setStyleSheet("font-size: 12px;")
        cl.addWidget(self.code_hint)
        root.addWidget(card, 1)

        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("SurfText")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        ok_btn = QPushButton("进入模拟模式")
        ok_btn.setObjectName("SurfFilled")
        ok_btn.clicked.connect(self._confirm)
        btns.addWidget(ok_btn)
        root.addLayout(btns)

    def _send_code(self):
        code = "%06d" % random.randint(0, 999999)
        self._code = code
        self.code_hint.setText(f"模拟验证码已发送：{code}（输入任意 6 位也可通过）")
        self.code_edit.setText(code)

    def _confirm(self):
        phone = self.phone_edit.text().strip()
        if not re.fullmatch(r"1\d{10}", phone):
            self.code_hint.setText("请输入正确的 11 位手机号")
            return
        code = self.code_edit.text().strip()
        if len(code) != 6:
            self.code_hint.setText("请输入 6 位验证码")
            return
        self.confirmed.emit(phone)
        self.accept()


# ---------------------------------------------------------------
# 登录窗口
# ---------------------------------------------------------------
class LoginWindow(QWidget):
    login_succeeded = Signal(object)   # cookies dict（API/模拟模式传 {}）

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._web_cookies: dict[str, str] = {}
        self._verifying = False
        self._verify_worker: VerifyWorker | None = None
        self._webview_created = False
        self.setWindowTitle("登录 - 菜鸟包裹监控")
        self.resize(820, 760)
        self.setMinimumSize(720, 680)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addStretch(1)

        # ---------- 居中玻璃卡片 ----------
        card = QFrame()
        card.setObjectName("SurfDialogCard")
        card.setMaximumWidth(660)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(32, 26, 32, 22)
        card_lay.setSpacing(14)

        # 品牌区
        brand = QHBoxLayout()
        brand.setSpacing(16)
        icon = QLabel()
        icon.setPixmap(make_app_icon(50).pixmap(50, 50))
        icon.setFixedSize(50, 50)
        brand.addWidget(icon)
        bt = QVBoxLayout()
        bt.setSpacing(2)
        title = QLabel("菜鸟包裹监控")
        tf = QFont("Segoe UI", 24)
        tf.setBold(True)
        title.setFont(tf)
        title.setStyleSheet(f"color: {COLOR_TEXT};")
        bt.addWidget(title)
        sub = QLabel("选择数据服务商 · 自动监控包裹物流 · 每 5 分钟刷新")
        sub.setObjectName("TxtSub")
        sub.setStyleSheet("font-size: 13px;")
        bt.addWidget(sub)
        brand.addLayout(bt)
        brand.addStretch(1)
        card_lay.addLayout(brand)

        # ---------- 服务商选择（4 个可选中卡片） ----------
        sel = QHBoxLayout()
        sel.setSpacing(10)
        self._providers = []
        for key, label in [("wuliu", "菜鸟账号"), ("kdniao", "快递鸟 API"),
                           ("kuaidi100", "快递100 API"), ("demo", "模拟模式")]:
            btn = QPushButton(label)
            btn.setObjectName("SurfNavItem")
            btn.setCheckable(True)
            btn.setMinimumHeight(40)
            btn.clicked.connect(lambda _=False, k=key: self._select_provider(k))
            sel.addWidget(btn, 1)
            self._providers.append((key, btn))
        card_lay.addLayout(sel)

        # ---------- 服务商配置区 ----------
        self._stack = QStackedLayout()
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._panel_wuliu = self._build_wuliu_panel()
        self._panel_kdniao = self._build_kdniao_panel()
        self._panel_kuaidi100 = self._build_kuaidi100_panel()
        self._panel_demo = self._build_demo_panel()
        self._stack.addWidget(self._panel_wuliu)
        self._stack.addWidget(self._panel_kdniao)
        self._stack.addWidget(self._panel_kuaidi100)
        self._stack.addWidget(self._panel_demo)
        card_lay.addLayout(self._stack, 1)

        # 底部状态
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setObjectName("TxtError")
        self.status_label.setStyleSheet("font-size: 13px;")
        self.status_label.setMinimumHeight(20)
        card_lay.addWidget(self.status_label)

        bottom = QHBoxLayout()
        hint = QLabel("API 密钥仅保存在本机 · Cookie 仅保存在本机")
        hint.setObjectName("TxtSub")
        hint.setStyleSheet("font-size: 11px;")
        bottom.addWidget(hint)
        bottom.addStretch(1)
        card_lay.addLayout(bottom)

        root.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter)
        root.addStretch(1)

        self._cookie_timer = QTimer(self)
        self._cookie_timer.setInterval(1500)
        self._cookie_timer.timeout.connect(self._check_web_cookies)
        self._cookie_timer.start()

        # 默认选中当前配置的服务商
        cur = self.config.get_provider()
        if cur == "demo":
            cur = "demo"
        self._select_provider(cur if cur in ("wuliu", "kdniao", "kuaidi100", "demo") else "wuliu")

    # ---------------------------------------------------------------
    # 服务商面板
    # ---------------------------------------------------------------
    def _select_provider(self, key: str) -> None:
        order = {"wuliu": 0, "kdniao": 1, "kuaidi100": 2, "demo": 3}
        self._stack.setCurrentIndex(order.get(key, 0))
        for k, btn in self._providers:
            btn.setChecked(k == key)

    # ---- 面板1：菜鸟账号 ----
    def _build_wuliu_panel(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(4, 8, 4, 4)
        lay.setSpacing(10)

        guide = QLabel("菜鸟账号 = 淘宝/菜鸟账号：登录会要求「短信验证码」（平台强制，验证码发到手机）。\n"
                       "新版菜鸟官网 www.cainiao.com 需登录查件，但其登录态与旧版查询接口不通用；\n"
                       "旧版授权页 wuliu.taobao.com 可能跳转淘宝登录——均属正常流程。\n"
                       "若旧接口不可用，请改用下方「快递鸟」或「快递100」（快递鸟已为你预配置）。")
        guide.setWordWrap(True)
        guide.setObjectName("TxtSub")
        guide.setStyleSheet("font-size: 13px;")
        lay.addWidget(guide)

        phone_row = QHBoxLayout()
        phone_lbl = QLabel("绑定手机号：")
        phone_lbl.setStyleSheet(f"color: {COLOR_TEXT_SUB}; font-size: 13px;")
        phone_row.addWidget(phone_lbl)
        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("用于短信验证码授权与快递查询手机尾号")
        self.phone_edit.setMaxLength(11)
        if self.config.get_phone():
            self.phone_edit.setText(self.config.get_phone())
        phone_row.addWidget(self.phone_edit, 1)
        lay.addLayout(phone_row)

        # 懒加载 WebEngine：点击才创建（避免部分环境 WebEngine 初始化崩溃）
        self._web_container = QWidget()
        self._web_lay = QVBoxLayout(self._web_container)
        self._web_lay.setContentsMargins(0, 0, 0, 0)
        self._web_lay.setSpacing(8)
        self._web_btn_row = QHBoxLayout()
        browser_btn = QPushButton("① 在系统浏览器中打开授权页（旧版接口入口）")
        browser_btn.setObjectName("SurfFilled")
        browser_btn.clicked.connect(lambda: webbrowser.open(WULIU_LIST))
        self._web_btn_row.addWidget(browser_btn)
        self._web_open_btn = QPushButton("② 应用内嵌浏览器（受限环境可能打不开）")
        self._web_open_btn.setObjectName("SurfTonal")
        self._web_open_btn.clicked.connect(self._open_webview)
        self._web_btn_row.addWidget(self._web_open_btn)
        self._web_btn_row.addStretch(1)
        self._web_lay.addLayout(self._web_btn_row)
        self._web_status = QLabel("")
        self._web_status.setObjectName("TxtSub")
        self._web_status.setStyleSheet("font-size: 12px;")
        self._web_lay.addWidget(self._web_status)
        lay.addWidget(self._web_container, 1)

        # 粘贴 Cookie（降级方案）
        sep = QLabel("或直接粘贴已登录浏览器的 Cookie（在 wuliu.taobao.com 登录后按 F12 → Console 输入 document.cookie 复制；仅旧版淘宝登录态可用于查询）")
        sep.setWordWrap(True)
        sep.setObjectName("TxtSub")
        sep.setStyleSheet("font-size: 12px;")
        lay.addWidget(sep)
        self.cookie_edit = QTextEdit()
        self.cookie_edit.setPlaceholderText("粘贴 Cookie：name1=value1; name2=value2; ...")
        self.cookie_edit.setMaximumHeight(64)
        lay.addWidget(self.cookie_edit)

        btns = QHBoxLayout()
        btns.addStretch(1)
        self.cookie_verify_btn = QPushButton("校验并登录")
        self.cookie_verify_btn.setObjectName("SurfFilled")
        self.cookie_verify_btn.clicked.connect(self._verify_cookie_text)
        btns.addWidget(self.cookie_verify_btn)
        lay.addLayout(btns)
        return page

    def _open_webview(self) -> None:
        if self._webview_created:
            return
        if not HAVE_WEBENGINE:
            webbrowser.open(WULIU_LIST)
            self._web_status.setText("当前版本未含内嵌浏览器，已在系统浏览器打开登录页，登录后复制 Cookie 粘贴到上方输入框。")
            return
        try:
            from PySide6.QtWebEngineWidgets import QWebEnginePage, QWebEngineView
            from PySide6.QtWebEngineCore import QWebEngineProfile
            self.webview = QWebEngineView()
            self.webview.setMinimumHeight(300)
            profile = QWebEngineProfile("cainiao_web", self.webview)
            try:
                profile.setPersistentCookiesPolicy(
                    QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
                profile.setPersistentStoragePath(os.path.join(app_data_dir(), "webprofile"))
            except Exception:
                pass
            page_obj = QWebEnginePage(profile, self.webview)
            self.webview.setPage(page_obj)
            try:
                self.webview.page().profile().cookieStore().cookieAdded.connect(
                    self._on_cookie_added)
            except Exception:
                pass
            self.webview.load(QUrl(WULIU_LIST))
            self._web_lay.insertWidget(0, self.webview, 1)
            self._webview_created = True
            self._web_open_btn.setText("重新加载授权页")
            self._web_open_btn.clicked.disconnect()
            self._web_open_btn.clicked.connect(lambda: self.webview.reload())
            self._web_status.setText("登录成功后本窗口会自动检测并继续…")
            self._web_loaded = False
            self._web_load_timer = QTimer(self)
            self._web_load_timer.setSingleShot(True)
            self._web_load_timer.setInterval(20000)
            self._web_load_timer.timeout.connect(self._on_web_load_timeout)
            self._web_load_timer.start()
            try:
                self.webview.loadFinished.connect(self._on_web_loaded)
            except Exception:
                pass
        except Exception as e:
            self._web_status.setText("内嵌浏览器初始化失败：" + str(e) + "（可用上方「粘贴 Cookie」方式登录）")

    # ---- 面板2：快递鸟 API ----
    def _build_kdniao_panel(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(4, 8, 4, 4)
        lay.setSpacing(10)
        tip = QLabel("快递鸟「即时查询」API（api.kdniao.com，需注册开发者账号获取）。\n"
                     "填写后即可按运单号查询全部主流快递物流。密钥仅保存在本机。")
        tip.setWordWrap(True)
        tip.setObjectName("TxtSub")
        tip.setStyleSheet("font-size: 13px;")
        lay.addWidget(tip)

        card = QFrame()
        card.setObjectName("SurfCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 16, 18, 16)
        cl.setSpacing(10)
        cl.addWidget(QLabel("EBusinessID（商户ID）"))
        self.kd_id_edit = QLineEdit()
        self.kd_id_edit.setPlaceholderText("如 1xxxxxxxxx")
        cl.addWidget(self.kd_id_edit)
        cl.addWidget(QLabel("AppKey（密钥）"))
        self.kd_key_edit = QLineEdit()
        self.kd_key_edit.setPlaceholderText("如 12345678-1234-1234-1234-xxxxxxxxxxxx")
        self.kd_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        cl.addWidget(self.kd_key_edit)
        cl.addWidget(QLabel("手机号（选填：部分快递如顺丰需收件人手机尾号才能查全）"))
        self.kd_phone_edit = QLineEdit()
        self.kd_phone_edit.setPlaceholderText("输入手机号即可，无需验证码")
        self.kd_phone_edit.setMaxLength(11)
        if self.config.get_phone():
            self.kd_phone_edit.setText(self.config.get_phone())
        cl.addWidget(self.kd_phone_edit)
        lay.addWidget(card, 1)

        kd = self.config.get_kdniao()
        if kd["ebusiness_id"]:
            self.kd_id_edit.setText(kd["ebusiness_id"])
        if kd["app_key"]:
            self.kd_key_edit.setText(kd["app_key"])

        btns = QHBoxLayout()
        btns.addStretch(1)
        save_btn = QPushButton("保存并进入")
        save_btn.setObjectName("SurfFilled")
        save_btn.clicked.connect(self._save_kdniao)
        btns.addWidget(save_btn)
        lay.addLayout(btns)
        return page

    def _save_kdniao(self) -> None:
        eid = self.kd_id_edit.text().strip()
        key = self.kd_key_edit.text().strip()
        if not eid or not key:
            self._set_status("请填写 EBusinessID 与 AppKey（还没有的话，可先选「模拟模式」体验）")
            return
        self.config.set_provider("kdniao")
        self.config.set_kdniao(eid, key)
        self.config.set_phone(self.kd_phone_edit.text().strip())
        self.config.set_demo(False)
        self.config.set_cookies({})
        self.login_succeeded.emit({})
        self.close()

    # ---- 面板3：快递100 API ----
    def _build_kuaidi100_panel(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(4, 8, 4, 4)
        lay.setSpacing(10)
        tip = QLabel("快递100 企业版「轮询查询」接口（poll.kuaidi100.com，需企业认证）。\n"
                     "未填写 key 时可使用「免费公开查询」模式（无需密钥，部分快递需要手机尾号）。")
        tip.setWordWrap(True)
        tip.setObjectName("TxtSub")
        tip.setStyleSheet("font-size: 13px;")
        lay.addWidget(tip)

        card = QFrame()
        card.setObjectName("SurfCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 16, 18, 16)
        cl.setSpacing(10)
        cl.addWidget(QLabel("customer（授权码）"))
        self.k100_customer_edit = QLineEdit()
        cl.addWidget(self.k100_customer_edit)
        cl.addWidget(QLabel("key（密钥）"))
        self.k100_key_edit = QLineEdit()
        self.k100_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        cl.addWidget(self.k100_key_edit)
        self.k100_free_check = QCheckBox("没有 key：使用免费公开查询模式")
        self.k100_free_check.setStyleSheet(f"color: {COLOR_TEXT_SUB}; font-size: 13px;")
        cl.addWidget(self.k100_free_check)
        cl.addWidget(QLabel("手机号（选填：部分快递如顺丰需收件人手机尾号才能查全）"))
        self.k100_phone_edit = QLineEdit()
        self.k100_phone_edit.setPlaceholderText("输入手机号即可，无需验证码")
        self.k100_phone_edit.setMaxLength(11)
        if self.config.get_phone():
            self.k100_phone_edit.setText(self.config.get_phone())
        cl.addWidget(self.k100_phone_edit)
        lay.addWidget(card, 1)

        api = self.config.get_kuaidi100_api()
        if api["customer"]:
            self.k100_customer_edit.setText(api["customer"])
        if api["key"]:
            self.k100_key_edit.setText(api["key"])
        if not api["customer"] and not api["key"]:
            self.k100_free_check.setChecked(True)

        btns = QHBoxLayout()
        btns.addStretch(1)
        save_btn = QPushButton("保存并进入")
        save_btn.setObjectName("SurfFilled")
        save_btn.clicked.connect(self._save_kuaidi100)
        btns.addWidget(save_btn)
        lay.addLayout(btns)
        return page

    def _save_kuaidi100(self) -> None:
        customer = self.k100_customer_edit.text().strip()
        key = self.k100_key_edit.text().strip()
        if not self.k100_free_check.isChecked() and (not customer or not key):
            self._set_status("请填写 customer 与 key，或勾选「免费公开查询模式」")
            return
        self.config.set_provider("kuaidi100")
        self.config.set_kuaidi100_api(customer, key)
        self.config.set_phone(self.k100_phone_edit.text().strip())
        self.config.set_demo(False)
        self.config.set_cookies({})
        self.login_succeeded.emit({})
        self.close()

    # ---- 面板4：模拟模式 ----
    def _build_demo_panel(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(4, 8, 4, 4)
        lay.setSpacing(10)
        tip = QLabel("模拟模式：无需任何账号/密钥，不连接服务器。\n"
                     "模拟「手机号 + 短信验证码」授权流程，并生成演示包裹数据，\n"
                     "完整体验：卡片列表 → 时间线/地图详情 → 5 分钟刷新 → 托盘通知。")
        tip.setWordWrap(True)
        tip.setStyleSheet(f"color: {COLOR_TEXT_SUB}; font-size: 13px;")
        lay.addWidget(tip)
        lay.addStretch(1)
        btns = QHBoxLayout()
        btns.addStretch(1)
        btn = QPushButton("进入模拟模式")
        btn.setObjectName("SurfFilled")
        btn.clicked.connect(self._open_simulation)
        btns.addWidget(btn)
        lay.addLayout(btns)
        return page

    def _open_simulation(self) -> None:
        dlg = SimulationDialog(self)
        dlg.confirmed.connect(self._enter_simulation)
        dlg.exec()

    def _enter_simulation(self, phone: str) -> None:
        self.config.set_provider("demo")
        self.config.set_demo(True)
        self.config.set_phone(phone)
        self.config.set_cookies({})
        self.login_succeeded.emit({})
        self.close()

    # ---------------------------------------------------------------
    # 菜鸟授权相关
    # ---------------------------------------------------------------
    def _on_web_loaded(self, ok: bool) -> None:
        self._web_loaded = True
        if hasattr(self, "_web_load_timer"):
            self._web_load_timer.stop()
        if not ok:
            self._set_status("提示：授权页加载失败。可直接用「粘贴 Cookie」方式登录，"
                             "或改用顶部「快递鸟 API / 快递100 API」服务商。")
            return
        # 检测服务端错误页（如"页面无法访问"），给出替代建议
        try:
            self.webview.page().runJavaScript(
                "document.body ? document.body.innerText.slice(0, 300) : ''",
                self._check_page_text)
        except Exception:
            pass

    def _check_page_text(self, text) -> None:
        if not text:
            return
        if "页面无法访问" in text or ("抱歉" in text and "无法" in text):
            self._set_status("菜鸟旧版授权页似乎已下线或被拦截："
                             "请改用顶部「快递鸟 API」或「快递100 API」服务商"
                             "（已为你配置快递鸟），或尝试「粘贴 Cookie」方式登录。")

    def _on_web_load_timeout(self) -> None:
        if not getattr(self, "_web_loaded", False):
            self._set_status("提示：授权页加载较慢或内嵌浏览器受限。可等待片刻，或改用「粘贴 Cookie」方式。")

    def _on_cookie_added(self, cookie) -> None:
        try:
            name = bytes(cookie.name()).decode("utf-8", "ignore")
            value = bytes(cookie.value()).decode("utf-8", "ignore")
            domain = cookie.domain() or ""
            if not name or not value:
                return
            if "taobao.com" in domain or "wuliu" in domain or not domain:
                self._web_cookies[name] = value
        except Exception:
            pass

    def _check_web_cookies(self) -> None:
        if self._verifying or not self._webview_created:
            return
        names = set(self._web_cookies)
        if names & {"cookie2", "sgcookie", "_tb_token_", "unb", "lgc", "uc1"}:
            self._verify(dict(self._web_cookies))

    def _verify_cookie_text(self) -> None:
        text = self.cookie_edit.toPlainText().strip()
        cookies = self._parse_cookie_text(text)
        if not cookies:
            self._set_status("未解析到任何 Cookie，请检查粘贴内容格式")
            return
        self._verify(cookies)

    @staticmethod
    def _parse_cookie_text(text: str) -> dict:
        out: dict[str, str] = {}
        text = text.strip()
        if not text:
            return out
        if text.startswith("{"):
            try:
                import json
                j = json.loads(text)
                if isinstance(j, dict):
                    for k, v in j.items():
                        if isinstance(v, str):
                            out[str(k)] = v
                    return out
            except Exception:
                pass
        for seg in re.split(r"[;\n]", text):
            seg = seg.strip()
            if "=" not in seg:
                continue
            k, v = seg.split("=", 1)
            k, v = k.strip(), v.strip().strip('"\'')
            if k and v:
                out[k] = v
        return out

    def _verify(self, cookies: dict) -> None:
        if self._verifying:
            return
        if not cookies:
            self._set_status("尚未获取到登录 Cookie，请先完成登录")
            return
        self._verifying = True
        self._set_status("正在校验登录状态…", error=False)
        phone = self.phone_edit.text().strip()
        self._verify_worker = VerifyWorker(cookies, self)
        self._verify_worker.ok.connect(lambda c: self._on_login_ok(c, phone))
        self._verify_worker.fail.connect(self._on_login_fail)
        self._verify_worker.start()

    def _on_login_ok(self, cookies: dict, phone: str) -> None:
        self._verifying = False
        clean = {k: v for k, v in cookies.items()
                 if any(d in k.lower() for d in ("cna", "cookie", "token", "unb", "lgc",
                                                 "uc1", "sg", "tb", "tracknick", "dnk", "x5sec"))}
        if not clean:
            clean = cookies
        self.config.set_provider("wuliu")
        self.config.set_demo(False)
        self.config.set_cookies(clean)
        if phone:
            self.config.set_phone(phone)
        self.login_succeeded.emit(clean)
        self.close()

    def _on_login_fail(self, msg: str) -> None:
        self._verifying = False
        self._set_status("登录失败：" + msg)

    def _set_status(self, text: str, error: bool = True) -> None:
        self.status_label.setObjectName("TxtError" if error else "TxtSuccess")
        self.status_label.setStyleSheet("font-size: 13px;")
        self.status_label.setText(text)

    def closeEvent(self, event) -> None:
        """关闭：非阻塞——校验线程分离到后台自然结束"""
        if self._verify_worker and self._verify_worker.isRunning():
            self._verify_worker.requestInterruption()
            from ..core.workers import detach_thread
            detach_thread(self._verify_worker)
            self._verify_worker = None
        super().closeEvent(event)

    # ---------- 背景（深色渐变 + 青蓝光斑） ----------
    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        from .theme import tk as _tk
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor(_tk("BG_TOP")))
        grad.setColorAt(1.0, QColor(_tk("BG_BOTTOM")))
        p.fillRect(self.rect(), grad)
        p.setPen(Qt.PenStyle.NoPen)
        r1 = QRadialGradient(self.width() * 0.78, self.height() * 0.15, 420)
        r1.setColorAt(0.0, QColor(0, 212, 255, 30))
        r1.setColorAt(1.0, QColor(0, 212, 255, 0))
        p.setBrush(r1)
        p.drawRect(self.rect())
        r2 = QRadialGradient(self.width() * 0.1, self.height() * 0.8, 360)
        r2.setColorAt(0.0, QColor(62, 123, 250, 34))
        r2.setColorAt(1.0, QColor(62, 123, 250, 0))
        p.setBrush(r2)
        p.drawRect(self.rect())
        p.end()
        super().paintEvent(event)
