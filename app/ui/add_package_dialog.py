# -*- coding: utf-8 -*-
"""手动添加运单 —— Material Design 3 对话框（快递100 数据源降级方案）"""
from __future__ import annotations

import re

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QComboBox, QDialog, QFrame, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QVBoxLayout)

from ..api.http_client import build_session
from ..api.kuaidi100 import query_package
from ..config import Config
from ..constants import (COLOR_BG_TOP, COLOR_ERR, COLOR_TEXT_SUB, COMPANIES)
from ..models import Package

TRACK_RE = re.compile(r"(?<![0-9A-Za-z])([A-Za-z]{0,4}\d{9,16})(?![0-9A-Za-z])")


class _AddWorker(QThread):
    done = Signal(object)   # Package
    failed = Signal(str)

    def __init__(self, mail_no: str, com100: str, phone_last4: str, parent=None):
        super().__init__(parent)
        self.mail_no = mail_no
        self.com100 = com100
        self.phone_last4 = phone_last4

    def run(self):
        session = build_session()
        try:
            pkg = query_package(session, self.mail_no, self.com100, self.phone_last4)
            self.done.emit(pkg)
        except Exception as e:
            self.failed.emit(str(e))


class AddPackageDialog(QDialog):
    """添加包裹对话框；添加成功发出 package_added(package)"""
    package_added = Signal(object)

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self._worker: _AddWorker | None = None
        self.setWindowTitle("添加包裹")
        self.setFixedSize(480, 360)
        self.setObjectName("SurfDialog")   # 背景由主题 QSS 提供（跟随深浅色）

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 26, 28, 24)
        root.setSpacing(14)

        tip = QLabel("账号模式不可用时，可手动添加运单号查询。"
                     "顺丰等部分快递需要手机号后四位才能查到完整轨迹。")
        tip.setWordWrap(True)
        tip.setObjectName("TxtSub")
        tip.setStyleSheet("font-size: 13px;")
        root.addWidget(tip)

        panel = QFrame()
        panel.setObjectName("SurfCard")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(12)

        lay.addWidget(QLabel("运单号"))
        row = QHBoxLayout()
        self.no_edit = QLineEdit()
        self.no_edit.setPlaceholderText("如 SF1234567890123")
        row.addWidget(self.no_edit, 1)
        detect_btn = QPushButton("从剪贴板识别")
        detect_btn.setObjectName("SurfText")
        detect_btn.clicked.connect(self._detect_clipboard)
        row.addWidget(detect_btn)
        lay.addLayout(row)

        lay.addWidget(QLabel("包裹类型"))
        self.type_combo = QComboBox()
        self.type_combo.addItem("收件（我收到的包裹）", "收件")
        self.type_combo.addItem("寄件（我寄出的包裹）", "寄件")
        lay.addWidget(self.type_combo)

        lay.addWidget(QLabel("快递公司"))
        self.combo = QComboBox()
        for code, name, short, color, com100 in COMPANIES:
            self.combo.addItem(f"{name}（{short}）", com100)
        lay.addWidget(self.combo)

        if config.phone_last4():
            # 已保存手机号：无需重复填写
            saved = QLabel("已保存手机尾号 " + config.phone_last4() + "（设置里可修改）")
            saved.setObjectName("TxtSub")
            saved.setStyleSheet("font-size: 12px;")
            lay.addWidget(saved)
            self.phone_edit = QLineEdit(config.phone_last4())
            self.phone_edit.setVisible(False)
        else:
            lay.addWidget(QLabel("手机号后四位（选填，部分快递需要）"))
            self.phone_edit = QLineEdit()
            self.phone_edit.setPlaceholderText("如 8888")
            self.phone_edit.setMaxLength(4)
            lay.addWidget(self.phone_edit)
        root.addWidget(panel, 1)

        self.err_label = QLabel("")
        self.err_label.setObjectName("TxtError")
        self.err_label.setStyleSheet("font-size: 13px;")
        self.err_label.setWordWrap(True)
        root.addWidget(self.err_label)

        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("SurfText")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        ok_btn = QPushButton("查询并添加")
        ok_btn.setObjectName("SurfFilled")
        ok_btn.clicked.connect(self._add)
        btns.addWidget(ok_btn)
        root.addLayout(btns)

        # 自动扫描剪贴板：打开时若剪贴板含运单号则自动填入
        self._auto_detect_clipboard()
        try:
            from PySide6.QtWidgets import QApplication as _QA
            _QA.clipboard().dataChanged.connect(self._on_clipboard_changed)
        except Exception:
            pass

    def _auto_detect_clipboard(self) -> None:
        """打开对话框时自动识别剪贴板中的运单号（无需手动点击）"""
        from PySide6.QtWidgets import QApplication
        text = QApplication.clipboard().text()
        m = TRACK_RE.search(text)
        if m and not self.no_edit.text().strip():
            self.no_edit.setText(m.group(1))
            self.err_label.setText("已自动识别运单号：%s" % m.group(1))

    def _on_clipboard_changed(self) -> None:
        """剪贴板变化且输入框为空时自动填入运单号"""
        if self.no_edit.text().strip():
            return
        self._auto_detect_clipboard()

    def _detect_clipboard(self) -> None:
        from PySide6.QtWidgets import QApplication
        text = QApplication.clipboard().text()
        m = TRACK_RE.search(text)
        if m:
            self.no_edit.setText(m.group(1))
            self.err_label.setText("已从剪贴板识别运单号：%s" % m.group(1))
        else:
            self.err_label.setText("剪贴板中没有找到运单号")

    def _add(self) -> None:
        mail_no = self.no_edit.text().strip()
        com100 = self.combo.currentData()
        phone = self.phone_edit.text().strip()
        if not mail_no:
            self.err_label.setText("请输入运单号")
            return
        if self._worker and self._worker.isRunning():
            return
        self.err_label.setText("正在查询…")
        self._worker = _AddWorker(mail_no, com100, phone, self)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_done(self, pkg: Package) -> None:
        self.config.add_manual_package({
            "mail_no": pkg.mail_no,
            "company_code": pkg.company_code,
            "company_name": pkg.company_name,
            "com100": self.combo.currentData(),
            "phone_last4": self.phone_edit.text().strip(),
            "pkg_type": str(self.type_combo.currentData()),
        })
        self.package_added.emit(pkg)
        self.accept()

    def _on_failed(self, msg: str) -> None:
        self.err_label.setText(msg)

    def closeEvent(self, event) -> None:
        """关闭：非阻塞——查询线程分离到后台自然结束"""
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()
            from ..core.workers import detach_thread
            detach_thread(self._worker)
            self._worker = None
        super().closeEvent(event)
