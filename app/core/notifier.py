# -*- coding: utf-8 -*-
"""系统托盘：图标、菜单、Windows 通知气泡"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from ..logger import get_logger

log = get_logger()


class TrayNotifier(QObject):
    """托盘对象 + 通知封装（单例使用）"""
    action_open = Signal()
    action_refresh = Signal()
    action_quit = Signal()

    def __init__(self, icon: QIcon, parent: QObject | None = None):
        super().__init__(parent)
        self.tray = QSystemTrayIcon(icon, parent)
        self.tray.setToolTip("菜鸟包裹监控")
        self._menu = QMenu()
        act_open = QAction("打开主界面", self)
        act_open.triggered.connect(self.action_open)
        act_refresh = QAction("立即刷新", self)
        act_refresh.triggered.connect(self.action_refresh)
        act_quit = QAction("退出", self)
        act_quit.triggered.connect(self.action_quit)
        self._menu.addAction(act_open)
        self._menu.addAction(act_refresh)
        self._menu.addSeparator()
        self._menu.addAction(act_quit)
        self.tray.setContextMenu(self._menu)
        self.tray.activated.connect(self._on_activated)
        self._first_hint_shown = False

    def _on_activated(self, reason) -> None:
        """双击任务栏托盘图标 -> 打开主界面（单窗口，不会重复弹出）"""
        try:
            from PySide6.QtWidgets import QSystemTrayIcon
            if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
                self.action_open.emit()
        except Exception:
            pass

    def show(self):
        self.tray.show()

    def hide(self):
        self.tray.hide()

    def set_tooltip(self, text: str):
        try:
            self.tray.setToolTip(text[:127])
        except Exception:
            pass

    def notify(self, title: str, body: str, urgent: bool = False) -> bool:
        """弹出 Windows 通知气泡。返回是否成功。"""
        try:
            if not self.tray.isVisible():
                self.tray.show()
            icon_type = (QSystemTrayIcon.MessageIcon.Warning if urgent
                         else QSystemTrayIcon.MessageIcon.Information)
            self.tray.showMessage(title[:64], body[:255], icon_type, 8000)
            return True
        except Exception as e:
            log.warning("tray notify failed: %s", e)
            return False

    def is_supported(self) -> bool:
        try:
            return QSystemTrayIcon.isSystemTrayAvailable()
        except Exception:
            return False
