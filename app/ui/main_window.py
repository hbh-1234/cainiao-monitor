# -*- coding: utf-8 -*-
"""主窗口 —— Surfboard 风格
- 顶部玻璃 TopBar：图标 + 标题/副标题 + 进行中 Chip + 刷新 + 齿轮(设置)
- 包裹页：筛选行（全部/已发货/已签收）+ 双列错位卡片（统一尺寸，右键删除）
- 设置：整窗从底部滑出/下滑关闭；子菜单整页左右滑动；模块化（通用/外观/账号）
"""
from __future__ import annotations

import os
import subprocess
import sys

from PySide6.QtCore import (QEasingCurve, QPoint, QPropertyAnimation, QRectF,
                            QSize, Qt, QTimer, Signal)
from PySide6.QtGui import (QAction, QColor, QFont, QLinearGradient,
                           QPainter, QPainterPath, QPen, QRadialGradient)
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QHBoxLayout,
                               QLabel, QLineEdit, QMenu, QMessageBox,
                               QPushButton, QScrollArea, QStackedLayout,
                               QToolButton, QVBoxLayout, QWidget)

from ..config import Config, app_data_dir
from ..constants import (COLOR_BG_BOTTOM, COLOR_BG_TOP, COLOR_TEXT_SUB)
from ..core.monitor import MonitorWorker
from ..core.notifier import TrayNotifier
from ..logger import get_logger
from ..models import Package
from .add_package_dialog import AddPackageDialog
from .detail_dialog import DetailDialog
from .icons import make_app_icon, m3_icon
from .package_card import PackageCard
from .staggered_layout import StaggeredLayout
from .theme import apply_theme, repolish_all, tk

log = get_logger()

# 预设配色系统（8 套，定义在 theme.py；此处仅引用）
from .theme import COLOR_SCHEMES, SCHEME_ORDER, scheme_colors


class SnackBar(QFrame):
    """Snackbar：底部居中，自动消失；info 深色玻璃，error 红色玻璃"""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("SurfSnackbar")
        self._label = QLabel(self)
        self._label.setWordWrap(True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 12, 18, 12)
        lay.addWidget(self._label)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self.hide()

    def show_message(self, text: str, kind: str = "info", timeout_ms: int = 3500) -> None:
        self._label.setText(text)
        self.setProperty("state", "error" if kind == "error" else "")
        self.style().unpolish(self)
        self.style().polish(self)
        self.adjustSize()
        self._timer.start(timeout_ms)
        self.raise_()
        self.show()

    def reposition(self) -> None:
        w = min(520, self.parent().width() - 32)
        self.resize(w, self.height())
        x = (self.parent().width() - w) // 2
        y = self.parent().height() - self.height() - 88
        self.move(x, y)


class DynamicIslandButton(QPushButton):
    """小正方形「+」按钮：深色边框 + 半透明背景 + 粗体加号（无文字）"""

    def __init__(self, parent=None):
        super().__init__("", parent)
        self.setFixedSize(44, 44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hover = False
        self.setMouseTracking(True)

    def enterEvent(self, e):
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        alpha = 210 if self._hover else 140
        path = QPainterPath()
        path.addRoundedRect(1, 1, w - 2, h - 2, 12, 12)
        p.setPen(QPen(QColor(60, 80, 120, 200), 1.6))
        p.setBrush(QColor(10, 17, 34, alpha))
        p.drawPath(path)
        gloss = QLinearGradient(0, 0, 0, h / 2)
        gloss.setColorAt(0.0, QColor(255, 255, 255, 28 if self._hover else 14))
        gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillPath(path, gloss)
        f = QFont("YouYuan", 22)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(255, 255, 255))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "+")
        p.end()

    def sizeHint(self):
        return QSize(44, 44)


class ToggleSwitch(QWidget):
    """iOS 风格拨动开关（不用方框按钮）"""
    toggled_on = Signal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(50, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, on: bool, silent: bool = False) -> None:
        self._checked = bool(on)
        self.update()
        if not silent:
            self.toggled_on.emit(self._checked)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_checked(not self._checked)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        if self._checked:
            track = QColor("#34C759")
        else:
            track = QColor(120, 130, 155, 120)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(0, 0, w, h, h / 2, h / 2)
        r = h - 6
        x = w - r - 3 if self._checked else 3
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(x, 3, r, r)
        p.end()


class _SchemeBlock(QPushButton):
    """配色方案块：方框内一个圆，圆内三种颜色（整体配色预览）"""

    def __init__(self, colors, parent=None):
        super().__init__(parent)
        self.colors = colors
        self.setFixedSize(56, 56)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        path = QPainterPath()
        path.addRoundedRect(1, 1, w - 2, h - 2, 12, 12)
        p.fillPath(path, QColor(255, 255, 255, 22))
        # 圆内三分色
        c1, c2, c3 = self.colors
        center = QRectF(8, 8, w - 16, h - 16)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(c1))
        p.drawPie(center, 90 * 16, 120 * 16)
        p.setBrush(QColor(c2))
        p.drawPie(center, 210 * 16, 120 * 16)
        p.setBrush(QColor(c3))
        p.drawPie(center, 330 * 16, 120 * 16)
        # 选中边框
        if self.isChecked():
            p.setPen(QPen(QColor(tk("ACCENT")), 2.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(1.5, 1.5, w - 3, h - 3, 12, 12)
        p.end()


def _divider() -> QFrame:
    d = QFrame()
    d.setObjectName("M3Divider")
    d.setFixedHeight(1)
    return d


class SettingsPanel(QWidget):
    """设置滑层：整窗覆盖；子菜单整页左右滑动"""

    PAGE_MAIN = 0
    PAGE_SOURCE = 1
    PAGE_LOG = 2
    PAGE_API = 3
    PAGE_INTERVAL = 4

    def __init__(self, main_win, config: Config):
        super().__init__(main_win)
        self.main = main_win
        self.config = config
        self._nav = 0
        self._anim: QPropertyAnimation | None = None
        self.setObjectName("SettingsRoot")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.hide()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- 顶栏：返回/关闭 + 标题 ----
        header = QFrame()
        header.setObjectName("SurfTopBar")
        header.setFixedHeight(56)
        hh = QHBoxLayout(header)
        hh.setContentsMargins(12, 8, 20, 8)
        self.back_btn = QPushButton("×")
        self.back_btn.setObjectName("SurfIcon")
        self.back_btn.setFixedSize(40, 40)
        self.back_btn.setStyleSheet("font-size: 24px; font-weight: 700;")
        self.back_btn.clicked.connect(self._on_back)
        hh.addWidget(self.back_btn)
        self._title = QLabel("设置")
        self._title.setObjectName("SurfTopTitle")
        hh.addWidget(self._title)
        hh.addStretch(1)
        root.addWidget(header)
        root.addStretch(1)          # 仅顶栏入布局：stretch 吸收余量，顶栏固定在顶部
        self._header = header
        self._header_h = header.height()

        # ---- 抽屉式子页：每个子页面独立，主设置页固定在下层 ----
        self._main_page = self._build_main_page()
        self._main_page.setObjectName("SettingsPage")
        self._main_page.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._main_page.setParent(self)
        self._main_page.show()
        self._sub_pages: dict[int, QWidget] = {}
        for idx, builder in ((self.PAGE_SOURCE, self._build_source_page),
                             (self.PAGE_LOG, self._build_log_page),
                             (self.PAGE_API, self._build_api_page),
                             (self.PAGE_INTERVAL, self._build_interval_page)):
            pg = builder()
            pg.setObjectName("SettingsPage")
            pg.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            pg.setParent(self)
            pg.hide()
            self._sub_pages[idx] = pg
        self._layout_pages()

    # ---------------------------------------------------------------
    def _layout_pages(self) -> None:
        """按当前尺寸摆放：主设置页铺满内容区，子页在右侧待命/盖在主页上"""
        w = self.width()
        h = max(0, self.height() - self._header_h)
        self._main_page.setGeometry(0, self._header_h, w, h)
        for i, pg in self._sub_pages.items():
            pg.setFixedWidth(w)
            pg.setFixedHeight(h)
            if pg.isVisible():
                pg.move(0, self._header_h)      # 正在展示的抽屉保持原位
            else:
                pg.move(w, self._header_h)      # 隐藏的抽屉停在右侧

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._layout_pages()

    PAGE_TITLES = {1: "数据来源说明", 2: "日志",
                   3: "API 服务商设置", 4: "刷新间隔"}

    def _stop_anim(self) -> None:
        anim = self._anim
        if anim:
            try:
                anim.stop()          # stop() 不会触发 finished，旧动画不会误隐藏面板
            except Exception:
                pass
            self._anim = None

    def _navigate(self, index: int, duration: int = 300) -> None:
        index = max(0, min(index, max(self._sub_pages)))
        if index == self._nav:
            return
        prev = self._nav
        self._nav = index
        self._stop_anim()
        self.back_btn.setText("<" if index else "×")
        self._title.setText(self.PAGE_TITLES.get(index, "设置"))
        w = self.width()
        y = self._header_h
        if index == 0:
            # 返回：抽屉向右拉出（推拉手感），主设置页随之露出
            pg = self._sub_pages.get(prev)
            self._main_page.raise_()
            if pg and pg.isVisible():
                anim = QPropertyAnimation(pg, b"pos", self)
                anim.setDuration(duration)
                anim.setStartValue(pg.pos())
                anim.setEndValue(QPoint(w, y))
                anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
                anim.finished.connect(pg.hide)
                anim.start()
                self._anim = anim
        else:
            # 前进：子页抽屉从右侧推入，盖在主设置页上
            pg = self._sub_pages[index]
            pg.setGeometry(w, y, w, self.height() - y)
            pg.show()
            pg.raise_()
            anim = QPropertyAnimation(pg, b"pos", self)
            anim.setDuration(duration)
            anim.setStartValue(QPoint(w, y))
            anim.setEndValue(QPoint(0, y))
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.start()
            self._anim = anim

    def _on_back(self) -> None:
        if self._nav:
            self._navigate(0)            # 子页返回：抽屉滑出回主设置页
        else:
            self.main._close_settings()

    def reset_pages(self) -> None:
        """重新打开设置时：回到主设置页，隐藏所有子页抽屉"""
        self._stop_anim()
        self._nav = 0
        self.back_btn.setText("×")
        self._title.setText("设置")
        self._main_page.show()
        self._main_page.raise_()
        self._layout_pages()
        for pg in self._sub_pages.values():
            pg.hide()

    # ---------------------------------------------------------------
    # 通用模块
    # ---------------------------------------------------------------
    def _row(self, text: str, slot, chevron: bool = True) -> QPushButton:
        b = QPushButton(text + ("  ›" if chevron else ""))
        b.setObjectName("SurfText")
        b.setStyleSheet("text-align: left; padding: 14px 18px; font-size: 15px;")
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        if slot:
            b.clicked.connect(slot)
        return b

    def _build_main_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(20, 16, 20, 30)
        bl.setSpacing(16)

        # ===== 通用 =====
        bl.addWidget(self._module_title("通用"))
        m1 = QFrame()
        m1.setObjectName("SurfCard")
        v1 = QVBoxLayout(m1)
        v1.setContentsMargins(0, 4, 0, 4)
        v1.setSpacing(0)
        v1.addWidget(self._row("数据来源说明", lambda: self._navigate(self.PAGE_SOURCE)))
        v1.addWidget(_divider())
        v1.addWidget(self._row("日志", lambda: self._navigate(self.PAGE_LOG)))
        v1.addWidget(_divider())
        v1.addWidget(self._row("API 服务商设置", lambda: self._navigate(self.PAGE_API)))
        v1.addWidget(_divider())
        v1.addWidget(self._row("刷新间隔", lambda: self._navigate(self.PAGE_INTERVAL)))
        v1.addWidget(_divider())
        # 免打扰（iOS 开关，不放方框按钮）
        dnd_row = QFrame()
        dnd_lay = QHBoxLayout(dnd_row)
        dnd_lay.setContentsMargins(18, 10, 18, 10)
        dnd_lbl = QLabel("免打扰（不弹通知）")
        dnd_lbl.setObjectName("TxtMain")
        dnd_lay.addWidget(dnd_lbl)
        dnd_lay.addStretch(1)
        self.dnd_switch = ToggleSwitch(self.config.is_dnd())
        self.dnd_switch.toggled_on.connect(self._on_dnd)
        dnd_lay.addWidget(self.dnd_switch)
        v1.addWidget(dnd_row)
        bl.addWidget(m1)

        # ===== 外观（展开，不折叠） =====
        bl.addWidget(self._module_title("外观"))
        m2 = QFrame()
        m2.setObjectName("SurfCard")
        v2 = QVBoxLayout(m2)
        v2.setContentsMargins(18, 16, 18, 18)
        v2.setSpacing(12)
        v2.addWidget(QLabel("主题"))
        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)
        self._mode_btns = []
        for key, label in (("system", "跟随系统"), ("dark", "深色"), ("light", "浅色")):
            b = QPushButton(label)
            b.setObjectName("SurfNavItem")
            b.setCheckable(True)
            b.setFixedHeight(38)
            b.clicked.connect(lambda _=False, k=key: self._set_mode(k))
            mode_row.addWidget(b, 1)
            self._mode_btns.append((key, b))
        v2.addLayout(mode_row)
        v2.addWidget(_divider())
        v2.addWidget(QLabel("配色"))
        scheme_row = QHBoxLayout()
        scheme_row.setSpacing(12)
        self._scheme_btns = []
        for name, colors in COLOR_SCHEMES.items():
            b = _SchemeBlock(colors)
            b.setToolTip(name)
            b.clicked.connect(lambda _=False, c=colors, n=name: self._set_scheme(n, c))
            scheme_row.addWidget(b)
            self._scheme_btns.append((name, b))
        scheme_row.addStretch(1)
        v2.addLayout(scheme_row)
        bl.addWidget(m2)

        # ===== 账号 =====
        bl.addWidget(self._module_title("账号"))
        m3 = QFrame()
        m3.setObjectName("SurfCard")
        v3 = QVBoxLayout(m3)
        v3.setContentsMargins(0, 4, 0, 4)
        v3.setSpacing(0)
        v3.addWidget(self._row("切换账号", self._on_switch_account))
        v3.addWidget(_divider())
        v3.addWidget(self._row("注销（清除信息并退出登录）", self._on_logout))
        v3.addWidget(_divider())
        v3.addWidget(self._row("退出（保留账号）", self._on_quit))
        bl.addWidget(m3)

        bl.addStretch(1)
        scroll.setWidget(body)
        lay.addWidget(scroll)
        return page

    def _module_title(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("TxtSub")
        lbl.setStyleSheet("font-size: 13px; font-weight: 700;")
        return lbl

    # ---------------------------------------------------------------
    def _build_source_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 16, 20, 20)
        lay.setSpacing(10)
        text = QLabel(
            "数据来源：\n"
            "1. 菜鸟账号 —— 手机号授权登录后自动同步账号下所有包裹；\n"
            "2. 快递鸟 API —— 按运单号查询（已配置）；\n"
            "3. 快递100 API —— 按运单号查询（或免费公开查询）。\n\n"
            "说明：\n"
            "• API 服务商只能按单号查询；要自动列出全部包裹请用「菜鸟账号」；\n"
            "• 物流信息来自第三方公开接口，仅供个人使用；\n"
            "• 页面改版导致解析失败时，原始页面会保存到数据目录 debug 文件夹。")
        text.setWordWrap(True)
        text.setStyleSheet("font-size: 14px; line-height: 1.5;")
        lay.addWidget(text)
        lay.addStretch(1)
        return page

    def _build_log_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 16, 20, 20)
        lay.setSpacing(12)
        tip = QLabel("日志与数据保存在本机数据目录，可打开查看：")
        tip.setStyleSheet("font-size: 14px;")
        lay.addWidget(tip)
        btn1 = QPushButton("打开数据目录")
        btn1.setObjectName("SurfTonal")
        btn1.clicked.connect(lambda: self.main._open_log_dir())
        lay.addWidget(btn1)
        lay.addStretch(1)
        return page

    def _build_api_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 16, 20, 20)
        lay.setSpacing(10)

        card = QFrame()
        card.setObjectName("SurfCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 16, 18, 16)
        cl.setSpacing(8)
        cl.addWidget(QLabel("数据服务商"))
        self.api_combo = QComboBox()
        self.api_combo.addItem("菜鸟账号（手机号授权）", "wuliu")
        self.api_combo.addItem("快递鸟 API", "kdniao")
        self.api_combo.addItem("快递100 API", "kuaidi100")
        self.api_combo.addItem("模拟模式", "demo")
        cur = self.config.get_provider()
        idx = [self.api_combo.itemData(i) for i in range(self.api_combo.count())].index(cur) if cur in ("wuliu", "kdniao", "kuaidi100", "demo") else 0
        self.api_combo.setCurrentIndex(idx)
        cl.addWidget(self.api_combo)

        cl.addWidget(QLabel("手机号（选填，用于查询尾号）"))
        self.api_phone = QLineEdit(self.config.get_phone())
        self.api_phone.setMaxLength(11)
        cl.addWidget(self.api_phone)

        cl.addWidget(QLabel("快递鸟 EBusinessID"))
        self.api_kd_id = QLineEdit()
        cl.addWidget(self.api_kd_id)
        cl.addWidget(QLabel("快递鸟 AppKey"))
        self.api_kd_key = QLineEdit()
        self.api_kd_key.setEchoMode(QLineEdit.EchoMode.Password)
        cl.addWidget(self.api_kd_key)
        cl.addWidget(QLabel("快递100 customer"))
        self.api_k100_cust = QLineEdit()
        cl.addWidget(self.api_k100_cust)
        cl.addWidget(QLabel("快递100 key"))
        self.api_k100_key = QLineEdit()
        self.api_k100_key.setEchoMode(QLineEdit.EchoMode.Password)
        cl.addWidget(self.api_k100_key)

        kd = self.config.get_kdniao()
        self.api_kd_id.setText(kd["ebusiness_id"])
        self.api_kd_key.setText(kd["app_key"])
        ka = self.config.get_kuaidi100_api()
        self.api_k100_cust.setText(ka["customer"])
        self.api_k100_key.setText(ka["key"])
        lay.addWidget(card, 1)

        save_btn = QPushButton("保存")
        save_btn.setObjectName("SurfFilled")
        save_btn.clicked.connect(self._on_api_save)
        lay.addWidget(save_btn)
        return page

    def _build_interval_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 16, 20, 20)
        lay.setSpacing(12)
        tip = QLabel("自动刷新间隔：")
        tip.setStyleSheet("font-size: 14px;")
        lay.addWidget(tip)
        row = QHBoxLayout()
        row.setSpacing(10)
        cur_min = self.config.refresh_minutes()
        self._interval_btns: list[tuple[int, QPushButton]] = []
        for mins in (1, 5, 10, 30, 60):
            b = QPushButton(f"{mins} 分钟")
            b.setObjectName("SurfNavItem")
            b.setCheckable(True)
            b.setChecked(mins == cur_min)
            b.setFixedHeight(38)
            b.clicked.connect(lambda _=False, m=mins: self._on_interval(m))
            row.addWidget(b, 1)
            self._interval_btns.append((mins, b))
        lay.addLayout(row)
        lay.addStretch(1)
        return page

    # ---------------------------------------------------------------
    # 行为
    # ---------------------------------------------------------------
    def _on_dnd(self, on: bool) -> None:
        self.config.set_dnd(on)
        self.main._snack.show_message("免打扰已" + ("开启" if on else "关闭"))

    def _set_mode(self, mode: str) -> None:
        for k, b in self._mode_btns:
            b.setChecked(k == mode)
        appr = self.config.get_appearance()
        self.config.set_appearance(mode, appr["scheme"],
                                   appr["accent"], appr["accent2"], appr["accent3"])
        self._apply_theme_now()

    def _set_scheme(self, name: str, colors) -> None:
        for n, b in self._scheme_btns:
            b.setChecked(n == name)
        appr = self.config.get_appearance()
        self.config.set_appearance(appr["mode"], name, *colors)
        self._apply_theme_now()

    def _apply_theme_now(self) -> None:
        from .theme import resolve_mode, scheme_colors
        appr = self.config.get_appearance()
        c1, c2, c3 = scheme_colors(appr["scheme"])
        app = QApplication.instance()
        apply_theme(app, resolve_mode(appr["mode"]), c1, c2, c3)
        repolish_all(app)
        self.main.refresh_icons()   # 顶栏图标随主题换色

    def _on_api_save(self) -> None:
        self.config.set_provider(str(self.api_combo.currentData()))
        self.config.set_phone(self.api_phone.text().strip())
        self.config.set_kdniao(self.api_kd_id.text().strip(), self.api_kd_key.text().strip())
        self.config.set_kuaidi100_api(self.api_k100_cust.text().strip(),
                                      self.api_k100_key.text().strip())
        self.config.set_demo(self.api_combo.currentData() == "demo")
        self.main._snack.show_message("服务商设置已保存，下次刷新生效")
        if self.config.get_provider() == "wuliu":
            self.main.relogin_requested.emit()

    def _on_interval(self, mins: int) -> None:
        # 单选：点哪个亮哪个，其余熄灭（避免多个同时亮）
        for m, b in self._interval_btns:
            b.setChecked(m == mins)
        self.config.set("settings", {**self.config.settings(), "refresh_min": mins})
        self.main._snack.show_message(f"刷新间隔已设为 {mins} 分钟")

    def _on_switch_account(self) -> None:
        self.main.relogin_requested.emit()

    def _on_logout(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("注销")
        box.setText("将删除 API 密钥、Cookie、手机号与手动运单，并退出登录。确定吗？")
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if box.exec() == QMessageBox.StandardButton.Yes:
            self.config.clear_private_data()
            self.main._snack.show_message("已清除全部个人信息")
            self.main.relogin_requested.emit()

    def _on_quit(self) -> None:
        self.main.quit_requested.emit()

    # 初始化外观控件状态
    def sync_ui(self) -> None:
        appr = self.config.get_appearance()
        for k, b in self._mode_btns:
            b.setChecked(k == appr["mode"])
        cur = appr["scheme"] if appr["scheme"] in dict(self._scheme_btns) else SCHEME_ORDER[0]
        for n, b in self._scheme_btns:
            b.setChecked(n == cur)


class MainWindow(QWidget):
    """主界面。需要外部调用 start_monitor() 启动后台刷新。"""
    relogin_requested = Signal()
    quit_requested = Signal()

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.monitor: MonitorWorker | None = None
        self.tray: TrayNotifier | None = None
        self._packages: list[Package] = []
        self._first_hide_hint = True
        self._filter = "all"

        self.setWindowTitle("菜鸟包裹监控")
        self.resize(1200, 800)
        self.setMinimumSize(920, 620)
        self.setWindowIcon(make_app_icon())

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---------- 顶部玻璃 TopBar ----------
        bar = QFrame()
        bar.setObjectName("SurfTopBar")
        bar.setFixedHeight(64)
        hh = QHBoxLayout(bar)
        hh.setContentsMargins(16, 6, 12, 6)
        hh.setSpacing(10)

        icon = QLabel()
        icon.setPixmap(make_app_icon(34).pixmap(34, 34))
        icon.setFixedSize(34, 34)
        hh.addWidget(icon)

        tt = QVBoxLayout()
        tt.setSpacing(0)
        title = QLabel("菜鸟包裹监控")
        title.setObjectName("SurfTopTitle")
        tt.addWidget(title)
        _provider_names = {"wuliu": "菜鸟账号", "kdniao": "快递鸟 API",
                          "kuaidi100": "快递100", "demo": "模拟数据"}
        self._sub = QLabel("数据来源：" + _provider_names.get(config.get_provider(), "菜鸟账号") + " · 未刷新")
        self._sub.setObjectName("SurfTopSub")
        tt.addWidget(self._sub)
        hh.addLayout(tt)
        hh.addStretch(1)

        self.count_chip = QLabel("进行中 0 件")
        self.count_chip.setProperty("chip", "cyan")
        self.count_chip.setStyleSheet("padding: 5px 14px; font-size: 13px;")
        hh.addWidget(self.count_chip)

        self.refresh_btn = QToolButton()
        self.refresh_btn.setObjectName("SurfIcon")
        self.refresh_btn.setIcon(m3_icon("refresh", 22, tk("TEXT")))
        self.refresh_btn.setIconSize(QSize(22, 22))
        self.refresh_btn.setFixedSize(38, 38)
        self.refresh_btn.setToolTip("立即刷新")
        self.refresh_btn.clicked.connect(self._manual_refresh)
        hh.addWidget(self.refresh_btn)

        # 齿轮（设置入口）
        self.gear_btn = QToolButton()
        self.gear_btn.setObjectName("SurfIcon")
        self.gear_btn.setIcon(m3_icon("gear", 22, tk("TEXT")))
        self.gear_btn.setIconSize(QSize(22, 22))
        self.gear_btn.setFixedSize(38, 38)
        self.gear_btn.setToolTip("设置")
        self.gear_btn.clicked.connect(self._open_settings)
        hh.addWidget(self.gear_btn)
        root.addWidget(bar)

        # ---------- 包裹页 ----------
        pkg_page = QWidget()
        pv = QVBoxLayout(pkg_page)
        pv.setContentsMargins(0, 0, 0, 0)
        pv.setSpacing(0)

        # 筛选行：全部 / 已发货（揽件+在途） / 已签收
        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(20, 12, 20, 0)
        filter_row.setSpacing(8)
        self._filter_btns = {}
        for key, label in [("all", "全部"), ("shipped", "已发货"), ("signed", "已签收")]:
            b = QPushButton(label)
            b.setObjectName("SurfNavItem")
            b.setCheckable(True)
            b.setFixedHeight(34)
            b.clicked.connect(lambda _=False, k=key: self._set_filter(k))
            filter_row.addWidget(b)
            self._filter_btns[key] = b
        self._filter_btns["all"].setChecked(True)
        filter_row.addStretch(1)
        pv.addLayout(filter_row)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._page = QWidget()
        self._page_stack = QStackedLayout(self._page)
        self._page_stack.setContentsMargins(0, 0, 0, 0)

        self._container = QWidget()
        # 双列错位布局：右列下移半卡，顶部空位留空
        self._flow = StaggeredLayout(self._container, margin=20,
                                     h_spacing=16, v_spacing=16, offset_ratio=0.5)
        self._page_stack.addWidget(self._container)

        # 空状态提示
        empty_page = QWidget()
        ev = QVBoxLayout(empty_page)
        ev.addStretch(1)
        from .icons import m3_icon_pixmap
        self._empty_icon = QLabel()
        self._empty_icon.setPixmap(m3_icon_pixmap("box", 72, tk("TEXT_SUB")))
        self._empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ev.addWidget(self._empty_icon)
        _provider_names2 = {"wuliu": "菜鸟账号", "kdniao": "快递鸟 API",
                            "kuaidi100": "快递100", "demo": "模拟数据"}
        _pname = _provider_names2.get(config.get_provider(), "菜鸟账号")
        _hint = ("当前数据源：%s。\n\n"
                 "· 想要自动列出你账号下所有包裹？切换到「菜鸟账号」服务商并完成手机号授权；\n"
                 "· %s 只能按运单号查询：复制运单号后点右下角「+」自动识别添加。"
                 % (_pname, _pname))
        self._empty = QLabel(_hint)
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setObjectName("TxtSub")
        self._empty.setStyleSheet("font-size: 15px; background: transparent;")
        ev.addWidget(self._empty)
        ev.addStretch(1)
        self._page_stack.addWidget(empty_page)

        self._scroll.setWidget(self._page)
        pv.addWidget(self._scroll, 1)
        root.addWidget(pkg_page, 1)

        # ---------- 小圆「+」按钮（悬浮右下） ----------
        self._fab = DynamicIslandButton()
        self._fab.setParent(self)
        self._fab.raise_()
        self._fab.setToolTip("添加运单（复制运单号后自动识别）")
        self._fab.clicked.connect(self._open_add_dialog)

        # ---------- Snackbar ----------
        self._snack = SnackBar(self)

        # ---------- 设置滑层 ----------
        self._settings = SettingsPanel(self, config)
        self._settings.raise_()
        self._update_fab_pos()

    # ---------------------------------------------------------------
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_fab_pos()
        self._snack.reposition()
        if self._settings.isVisible():
            self._settings.setGeometry(self.rect())

    def _update_fab_pos(self) -> None:
        if not hasattr(self, "_fab"):
            return
        self._fab.move(self.width() - self._fab.width() - 20,
                       self.height() - self._fab.height() - 20)
        self._fab.raise_()

    # ---------- 设置滑层（抽屉式：从底部滑入/滑出） ----------
    def _stop_settings_anim(self) -> None:
        anim = getattr(self, "_settings_anim", None)
        if anim:
            try:
                anim.stop()          # stop() 不触发 finished，旧动画不会误隐藏新面板
            except Exception:
                pass
            self._settings_anim = None

    def _open_settings(self) -> None:
        self._stop_settings_anim()
        h = self.height()
        # 先把面板定位到窗口底部之外再显示 → 打开过程不会闪出任何内容
        self._settings.setGeometry(0, h, self.width(), h)
        self._settings.reset_pages()
        self._settings.sync_ui()
        self._settings.show()      # 显示时在窗口之外，不可见；随后抽屉式滑入
        self._settings.raise_()
        self._fab.hide()           # 设置滑层打开时隐藏悬浮「+」
        anim = QPropertyAnimation(self._settings, b"pos", self)
        anim.setDuration(300)
        anim.setStartValue(QPoint(0, h))
        anim.setEndValue(QPoint(0, 0))
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        self._settings_anim = anim

    def _close_settings(self) -> None:
        self._stop_settings_anim()
        anim = QPropertyAnimation(self._settings, b"pos", self)
        anim.setDuration(250)
        anim.setStartValue(self._settings.pos())
        anim.setEndValue(QPoint(0, self.height()))
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        anim.finished.connect(self._settings.hide)
        anim.finished.connect(self._on_settings_closed)
        anim.start()
        self._settings_anim = anim

    def _on_settings_closed(self) -> None:
        self._settings_anim = None
        self._fab.show()
        self._update_fab_pos()

    # ===============================================================
    # 监控线程
    # ===============================================================
    def start_monitor(self) -> None:
        if self.monitor and self.monitor.isRunning():
            return
        self.monitor = MonitorWorker(self.config, self)
        self.monitor.packages_ready.connect(self.on_packages)
        self.monitor.updates_detected.connect(self.on_updates)
        self.monitor.error_occurred.connect(self.on_error)
        self.monitor.login_expired.connect(self.on_login_expired)
        self.monitor.status_changed.connect(self.on_status)
        self.monitor.start()

    def stop_monitor(self) -> None:
        if self.monitor and self.monitor.isRunning():
            self.monitor.stop()
            waited = 0
            while self.monitor.isRunning() and waited < 20000:
                self.monitor.wait(2000)
                waited += 2000

    def _manual_refresh(self) -> None:
        if self.monitor:
            self.monitor.refresh_now()
            self._sub.setText("正在刷新…")

    # ===============================================================
    # 监控回调（主线程）
    # ===============================================================
    def on_packages(self, packages: list) -> None:
        self._packages = list(packages)
        self._render_cards()
        self.count_chip.setText(f"进行中 {len(self._packages)} 件")

    def _set_filter(self, key: str) -> None:
        self._filter = key
        for k, b in self._filter_btns.items():
            b.setChecked(k == key)
        self._render_cards()

    def _filtered_packages(self) -> list:
        if self._filter == "shipped":
            return [p for p in self._packages
                    if p.state in ("transporting", "delivering")]
        if self._filter == "signed":
            return [p for p in self._packages if p.state == "signed"]
        return list(self._packages)

    def _render_cards(self) -> None:
        while self._flow.count():
            item = self._flow.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        shown = self._filtered_packages()
        if shown:
            self._page_stack.setCurrentIndex(0)
            for pkg in shown:
                card = PackageCard(pkg)
                card.clicked.connect(self._open_detail)
                card.delete_requested.connect(self._delete_package)
                self._flow.addWidget(card)
        else:
            self._page_stack.setCurrentIndex(1)

    def _delete_package(self, pkg: Package) -> None:
        if pkg.source in ("kdniao", "kuaidi100"):
            self.config.remove_manual_package(pkg.mail_no)
            self._packages = [p for p in self._packages if p.mail_no != pkg.mail_no]
            self._render_cards()
            self.count_chip.setText(f"进行中 {len(self._packages)} 件")
            self._snack.show_message("已删除运单 " + pkg.masked_no())
            self._manual_refresh()
        elif pkg.source == "wuliu":
            self._snack.show_message("账号同步的包裹无法删除（可在菜鸟账号内处理）", kind="error")
        else:
            self._packages = [p for p in self._packages if p.mail_no != pkg.mail_no]
            self._render_cards()
            self.count_chip.setText(f"进行中 {len(self._packages)} 件")
            self._snack.show_message("已从列表移除 " + pkg.masked_no())

    def on_updates(self, updated: list) -> None:
        if not updated:
            return
        settings = self.config.settings()
        if not settings.get("notify_enabled", True):
            return
        if self.config.is_dnd():
            return
        for item in updated[:5]:
            pkg: Package = item["package"]
            head = pkg.trace[0] if pkg.trace else None
            body = (head.status if head else pkg.latest_status) or "状态已更新"
            if self.tray:
                self.tray.notify(
                    f"包裹更新：{pkg.company_name} {pkg.masked_no()}",
                    f"{pkg.latest_time or ''}  {body}")
        if len(updated) > 5 and self.tray:
            self.tray.notify("包裹更新", f"还有 {len(updated) - 5} 个包裹有新的物流动态")

    def on_error(self, msg: str) -> None:
        log.warning("monitor error: %s", msg)
        self._snack.show_message(msg, kind="error", timeout_ms=5000)

    def on_status(self, msg: str) -> None:
        self._sub.setText(msg)
        if self.tray:
            self.tray.set_tooltip("菜鸟包裹监控 - " + msg)

    def show_status(self, text: str, kind: str = "info") -> None:
        self._snack.show_message(text, kind=kind)

    def on_login_expired(self) -> None:
        self.stop_monitor()
        self._sub.setText("登录态已失效")
        box = QMessageBox(self)
        box.setWindowTitle("登录已失效")
        box.setText("登录状态已过期，需要重新登录后才能继续获取包裹数据。")
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.exec()
        self.relogin_requested.emit()

    # ===============================================================
    # 交互
    # ===============================================================
    def _open_detail(self, package: Package) -> None:
        dlg = DetailDialog(package, self.config, self)
        dlg.exec()

    def _open_add_dialog(self) -> None:
        dlg = AddPackageDialog(self.config, self)
        dlg.package_added.connect(lambda p: self._manual_refresh())
        dlg.exec()

    def _open_log_dir(self) -> None:
        d = app_data_dir()
        try:
            if sys.platform == "win32":
                os.startfile(d)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["open", d])
        except Exception:
            QMessageBox.information(self, "数据目录", d)

    # ===============================================================
    # 托盘 / 关闭行为
    # ===============================================================
    def set_tray(self, tray: TrayNotifier) -> None:
        self.tray = tray
        tray.action_open.connect(self._show_from_tray)
        tray.action_refresh.connect(self._manual_refresh)
        tray.action_quit.connect(self.quit_requested)

    def _show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def refresh_icons(self) -> None:
        """主题切换后重绘主题相关图标（顶栏按钮/空状态）"""
        try:
            if hasattr(self, "refresh_btn"):
                self.refresh_btn.setIcon(m3_icon("refresh", 22, tk("TEXT")))
            if hasattr(self, "gear_btn"):
                self.gear_btn.setIcon(m3_icon("gear", 22, tk("TEXT")))
            if hasattr(self, "_empty_icon"):
                self._empty_icon.setPixmap(m3_icon_pixmap("box", 72, tk("TEXT_SUB")))
        except Exception:
            pass

    def closeEvent(self, event) -> None:
        if self.tray and self.tray.is_supported() and self.tray.tray.isVisible():
            event.ignore()
            self.hide()
            if self._first_hide_hint:
                self._first_hide_hint = False
                self.tray.notify("菜鸟包裹监控仍在运行",
                                 "已最小化到系统托盘，右击托盘图标可退出。")
        else:
            event.accept()

    # ---------- 背景（深色渐变 + 三色光斑） ----------
    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor(tk("BG_TOP")))
        grad.setColorAt(1.0, QColor(tk("BG_BOTTOM")))
        p.fillRect(self.rect(), grad)
        p.setPen(Qt.PenStyle.NoPen)
        # 三色半透明光斑（主/次/三级色）
        def glow(xr, yr, rr, color, alpha):
            g = QRadialGradient(xr, yr, rr)
            c = QColor(color)
            c.setAlpha(alpha)
            g.setColorAt(0.0, c)
            c2 = QColor(color)
            c2.setAlpha(0)
            g.setColorAt(1.0, c2)
            p.setBrush(g)
            p.drawRect(self.rect())
        glow(self.width() * 0.78, self.height() * 0.12, 380, tk("ACCENT"), 26)
        glow(self.width() * 0.12, self.height() * 0.85, 360, tk("ACCENT_BLUE"), 30)
        glow(self.width() * 0.55, self.height() * 0.5, 260, tk("TERTIARY"), 16)
        p.end()
        super().paintEvent(event)
