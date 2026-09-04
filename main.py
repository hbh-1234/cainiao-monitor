# -*- coding: utf-8 -*-
"""菜鸟包裹监控 —— 程序入口
用法：
    python main.py                  # 正常启动（手机号+短信验证码授权登录）
    python main.py --simulate       # 模拟模式：无需手机号/不联网，走完整监控流程
    python main.py --demo           # 纯界面演示（静态模拟数据）
    python main.py --no-webengine   # 不使用内嵌浏览器（精简打包时）
"""
from __future__ import annotations

import os
import sys
import traceback

from PySide6.QtCore import Qt, QDir, QLockFile, QTimer
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QMessageBox, QVBoxLayout

from app.config import Config, app_data_dir
from app.logger import get_logger

log = None

# 调试钩子：设置环境变量 CAINIAO_DEBUG_HANG=<文件路径> 后，
# 若程序在 8 秒内未退出，会把所有线程的堆栈写入该文件（排查"无窗口/卡死"问题）
if os.environ.get("CAINIAO_DEBUG_HANG"):
    try:
        import faulthandler
        faulthandler.dump_traceback_later(
            8, exit=False,
            file=open(os.environ["CAINIAO_DEBUG_HANG"], "w", encoding="utf-8"))
    except Exception:
        pass


def _install_excepthook(app: QApplication) -> None:
    """全局异常兜底：记录日志并弹窗提示，避免程序无声崩溃"""
    def hook(exc_type, exc_value, exc_tb):
        detail = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        if log:
            log.critical("unhandled exception:\n%s", detail)
        try:
            QMessageBox.critical(
                None, "程序发生错误",
                "很抱歉，程序遇到了一个未预期的错误：\n\n"
                + str(exc_value) + "\n\n详细信息已写入日志文件。")
        except Exception:
            pass
    sys.excepthook = hook


class _Splash(QFrame):
    """启动校验登录状态时的简易加载框"""

    def __init__(self, text: str = "正在验证登录状态…"):
        super().__init__(None)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint)
        self.setObjectName("M3DialogCard")
        self.setFixedSize(340, 100)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 14, 20, 14)
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #1c2b45;")
        lay.addWidget(lbl)


def _log_gui_env() -> None:
    """记录 GUI 环境：进程所在桌面、屏幕数量与几何（排查"窗口不显示"）"""
    try:
        import ctypes
        h = ctypes.windll.user32.GetThreadDesktop(
            ctypes.windll.kernel32.GetCurrentThreadId())
        buf = ctypes.create_unicode_buffer(256)
        ok = ctypes.windll.user32.GetUserObjectInformationW(h, 2, buf, 512, None)
        log.info("GUI desktop: %r", buf.value if ok else "?")
        from PySide6.QtGui import QGuiApplication
        scr = QGuiApplication.screens()
        log.info("GUI screens: %d", len(scr))
        if scr:
            g = scr[0].availableGeometry()
            log.info("screen0: %dx%d at (%d,%d)", g.width(), g.height(), g.x(), g.y())
    except Exception as e:
        log.warning("gui env probe failed: %s", e)


def _save_window_shot(widget, tag: str) -> None:
    """调试截图：把窗口内容保存为 PNG（用于无可见桌面的环境确认界面）"""
    try:
        from app.config import app_data_dir
        d = os.path.join(app_data_dir(), "debug")
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, f"window_{tag}.png")
        ok = widget.grab().save(path)
        log.info("debug screenshot %s -> %s (ok=%s)", tag, path, ok)
    except Exception as e:
        log.warning("debug screenshot failed: %s", e)


def _center_on_screen(widget) -> None:
    from PySide6.QtGui import QGuiApplication
    scr = QGuiApplication.primaryScreen().availableGeometry()
    widget.move(scr.center() - widget.rect().center())


def main() -> int:
    global log
    no_webengine = "--no-webengine" in sys.argv
    demo_mode = "--demo" in sys.argv
    # 模拟模式标志文件（启动菜鸟监控-模拟模式.cmd 创建，explorer 启动无法传参）
    _sim_flag = None
    for _base in ([os.path.dirname(sys.executable)] if getattr(sys, "frozen", False) else []) + [os.getcwd()]:
        _p = os.path.join(_base, "模拟模式.flag")
        if os.path.isfile(_p):
            _sim_flag = _p
            break
    if _sim_flag:
        try:
            os.remove(_sim_flag)
        except Exception:
            pass
    simulate_mode = "--simulate" in sys.argv or _sim_flag is not None
    shot_debug = "--shot" in sys.argv or os.environ.get("CAINIAO_DEBUG_SHOT") == "1"
    if no_webengine:
        os.environ["CAINIAO_NO_WEBENGINE"] = "1"
    # 受限环境逃生开关：内嵌浏览器白屏/无法加载时使用
    # （python main.py --no-sandbox 或设置环境变量 CAINIAO_NO_SANDBOX=1）
    if "--no-sandbox" in sys.argv or os.environ.get("CAINIAO_NO_SANDBOX") == "1":
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox --disable-gpu"

    # WebEngine 要求：在创建 QApplication 之前设置
    from PySide6.QtCore import QCoreApplication
    if not no_webengine:
        QCoreApplication.setAttribute(
            Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

    from PySide6.QtWidgets import QApplication as QA
    app = QA(sys.argv)
    app.setApplicationName("CainiaoMonitor")
    app.setApplicationDisplayName("菜鸟包裹监控")
    app.setOrganizationName("CainiaoMonitor")
    app.setQuitOnLastWindowClosed(False)   # 关窗不退出（托盘常驻）

    from app.logger import setup_logger
    log = setup_logger()
    log.info("== 菜鸟包裹监控启动 ==")
    _log_gui_env()
    config0 = Config()
    appr = config0.get_appearance()
    from app.ui.theme import apply_theme, resolve_mode, scheme_colors
    c1, c2, c3 = scheme_colors(appr["scheme"])   # 方案表为准，旧配色自动回退第1张
    apply_theme(app, mode=resolve_mode(appr["mode"]), accent=c1, accent2=c2, accent3=c3)
    log.info("theme applied: %s / %s", appr["mode"], appr["scheme"])
    from app.ui.icons import make_app_icon
    app.setWindowIcon(make_app_icon())
    _install_excepthook(app)
    log.info("excepthook installed")

    # 单实例锁（stale=30s：进程崩溃后锁自动失效，但运行中的实例不会被抢）
    lock = QLockFile(QDir.temp().filePath("cainiao_monitor.lock"))
    lock.setStaleLockTime(30000)
    if not lock.tryLock(100):
        # 已在运行：静默退出，避免重复窗口/重复弹窗
        log.info("已有实例在运行，本实例退出")
        return 0

    config = config0
    log.info("config loaded, demo=%s cookies=%s", config.is_demo(), bool(config.get_cookies()))

    if demo_mode:
        app.setQuitOnLastWindowClosed(True)   # 演示模式：关窗即退出
        _run_demo(app, config)
        return app.exec()

    # ---------- 启动流程 ----------
    from app.ui.login_window import LoginWindow, VerifyWorker
    from app.ui.main_window import MainWindow

    main_win: MainWindow | None = None
    splash: _Splash | None = None

    def show_login(hint: str = "") -> None:
        nonlocal splash
        if splash:
            splash.close()
            splash = None
        log.info("show_login: constructing LoginWindow")
        lw = LoginWindow(config)
        log.info("show_login: LoginWindow constructed")
        if hint:
            lw._set_status(hint)
        lw.login_succeeded.connect(lambda c: go_main(c))
        # 未登录直接关闭窗口 → 程序退出（托盘未启动前）
        lw.destroyed.connect(lambda: app.quit() if main_win is None else None)
        lw.show()
        lw.raise_()
        lw.activateWindow()
        log.info("login window shown, visible=%s size=%dx%d",
                 lw.isVisible(), lw.width(), lw.height())
        try:
            _center_on_screen(lw)
        except Exception as e:
            log.warning("center_on_screen failed: %s", e)
        if shot_debug:
            QTimer.singleShot(2500, lambda: _save_window_shot(lw, "login"))

    def go_main(cookies: dict | None = None) -> None:
        nonlocal main_win, splash
        if cookies:
            config.set_cookies(cookies)
        if splash:
            splash.close()
            splash = None
        if main_win is None:
            main_win = MainWindow(config)
            main_win.relogin_requested.connect(handle_relogin)
            main_win.quit_requested.connect(handle_quit)
            from app.core.notifier import TrayNotifier
            tray = TrayNotifier(make_app_icon(), main_win)
            tray.show()
            main_win.set_tray(tray)
        main_win.show()
        main_win.raise_()
        main_win.activateWindow()
        _center_on_screen(main_win)
        if shot_debug:
            QTimer.singleShot(2500, lambda: _save_window_shot(main_win, "main"))
        main_win.start_monitor()

    def handle_relogin() -> None:
        nonlocal main_win
        if main_win:
            main_win.stop_monitor()
            main_win.hide()
        show_login()

    def cleanup() -> None:
        """退出前兜底：确保监控线程已停止、后台分离线程已结束"""
        try:
            if main_win and main_win.monitor and main_win.monitor.isRunning():
                main_win.stop_monitor()
        except Exception:
            pass
        try:
            from app.core.workers import wait_all
            wait_all(8000)
        except Exception:
            pass

    app.aboutToQuit.connect(cleanup)

    def handle_quit() -> None:
        nonlocal main_win
        if main_win:
            main_win.stop_monitor()
            try:
                if main_win.tray:
                    main_win.tray.hide()
            except Exception:
                pass
        app.quit()

    # 模拟模式：无需登录，直接进入主界面（监控线程使用演示数据）
    if simulate_mode:
        log.info("simulate mode (runtime only, not persisted)")
        config.set_runtime_demo(True)
        go_main()
        return app.exec()

    # 已选择模拟模式（上次的记忆）→ 直接进主界面
    if config.is_demo():
        config.set_provider("demo")
        go_main()
        return app.exec()

    # API 服务商已配置密钥（快递鸟/快递100）→ 跳过登录直接进主界面
    if config.get_provider() in ("kdniao", "kuaidi100") and config.has_api_credentials():
        log.info("api provider configured: %s, skip login", config.get_provider())
        go_main()
        return app.exec()

    # 已有 Cookie：先校验再进主界面；否则直接去登录
    if config.get_cookies():
        splash = _Splash()
        splash.show()
        _center_on_screen(splash)
        app.processEvents()
        worker = VerifyWorker(config.get_cookies())
        worker.ok.connect(lambda c: go_main(c))
        worker.fail.connect(lambda msg: show_login("自动登录失败：" + msg))
        worker.start()
    else:
        show_login()
    return app.exec()


def _run_demo(app: QApplication, config: Config) -> None:
    """演示模式：用模拟数据展示界面效果（不联网）"""
    from app.models import Package, TraceNode
    from app.ui.main_window import MainWindow

    now = "2025-06-08 14:32:10"
    demo = [
        Package(mail_no="SF1427395820135", company_code="SF",
                latest_status="快件已到达【杭州转运中心】，准备发往下一站",
                latest_time=now, state="transporting",
                trace=[TraceNode(time=now, status="快件已到达【杭州转运中心】，准备发往下一站"),
                       TraceNode(time="2025-06-08 08:12:00", status="快件在【上海浦东新区】已装车"),
                       TraceNode(time="2025-06-07 22:40:00", status="快件已从【上海浦东新区】发出"),
                       TraceNode(time="2025-06-07 18:05:00", status="顺丰速运已收取快件")]),
        Package(mail_no="YT7684951203498", company_code="YTO",
                latest_status="派件中，快递员正在为您派送",
                latest_time="2025-06-08 13:05:44", state="delivering",
                trace=[TraceNode(time="2025-06-08 13:05:44", status="派件中，快递员正在为您派送"),
                       TraceNode(time="2025-06-08 09:30:00", status="快件已到达【杭州市西湖区】网点"),
                       TraceNode(time="2025-06-07 20:15:00", status="快件在【金华转运中心】完成分拣"),
                       TraceNode(time="2025-06-07 10:00:00", status="商家已发货，等待揽收")]),
        Package(mail_no="JT9912045612377", company_code="JT",
                latest_status="快件已签收，签收人：菜鸟驿站（代收）",
                latest_time="2025-06-07 11:20:00", state="signed",
                trace=[TraceNode(time="2025-06-07 11:20:00", status="快件已签收，签收人：菜鸟驿站（代收）"),
                       TraceNode(time="2025-06-07 09:00:00", status="派件中"),
                       TraceNode(time="2025-06-06 16:30:00", status="快件已到达【杭州市下城区】网点")]),
    ]
    win = MainWindow(config)
    win.on_packages(demo)
    win.show()
    win.show_status("演示模式：数据为模拟数据，未连接网络")


if __name__ == "__main__":
    sys.exit(main())
