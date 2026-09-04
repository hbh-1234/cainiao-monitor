# -*- coding: utf-8 -*-
"""包裹详情弹窗 —— 仅时间线视图（地图功能已移除）
- 完整物流时间线（倒序，最新在顶部），窗口固定为半宽
"""
from __future__ import annotations

import webbrowser

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel,
                               QMessageBox, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

from ..api.http_client import build_session
from ..api.kuaidi100 import query as kuaidi100_query
from ..api.wuliu import fetch_detail as wuliu_fetch_detail
from ..config import Config
from ..constants import COLOR_ACCENT, com100_of
from ..models import Package, TraceNode, sort_trace_desc
from .icons import company_badge
from .package_card import state_chip_key

_STATE_TEXT = {"transporting": "运输中", "delivering": "派送中",
               "signed": "已签收", "problem": "异常"}


# ---------------------------------------------------------------
# 详情抓取线程
# ---------------------------------------------------------------
class DetailWorker(QThread):
    ready = Signal(object)     # nodes（时间线）
    failed = Signal(str)

    def __init__(self, package: Package, config: Config, parent=None):
        super().__init__(parent)
        self.package = package
        self.config = config

    def run(self):
        # 模拟模式：直接用演示数据（不联网）
        if self.config.is_demo() or self.package.source == "demo":
            nodes = list(self.package.trace)
            self.ready.emit(nodes)
            return
        session = build_session(self.config.get_cookies())
        nodes: list[TraceNode] = []
        last_err = ""
        phone = str(self.package.extra.get("phone_last4") or "") or self.config.phone_last4()

        provider = self.config.get_provider()
        if provider == "kdniao":
            # 快递鸟 API 详情
            try:
                from ..api.kdniao import query as kd_query
                cred = self.config.get_kdniao()
                nodes, _state = kd_query(session, cred["ebusiness_id"], cred["app_key"],
                                         self.package.mail_no,
                                         self.package.company_code, phone)
            except Exception as e:
                last_err = str(e)
        elif provider == "kuaidi100":
            # 快递100 详情（企业 key 优先，否则公开查询）
            try:
                api = self.config.get_kuaidi100_api()
                com100 = com100_of(self.package.company_code)
                if api["customer"] and api["key"]:
                    from ..api.kuaidi100 import query_official
                    nodes, _state = query_official(session, api["customer"], api["key"],
                                                   self.package.mail_no, com100, phone)
                else:
                    nodes, _state = kuaidi100_query(session, self.package.mail_no,
                                                    com100, phone)
            except Exception as e:
                last_err = str(e)
        else:
            # 默认：优先快递100；失败再用淘宝物流助手详情页
            com100 = com100_of(self.package.company_code)
            if com100:
                try:
                    nodes, _state = kuaidi100_query(session, self.package.mail_no,
                                                    com100, phone)
                except Exception as e:
                    last_err = str(e)
            if self.isInterruptionRequested():
                return
            if not nodes and self.config.get_cookies():
                try:
                    nodes = wuliu_fetch_detail(session, self.package.mail_no,
                                               self.package.company_code)
                except Exception as e:
                    if not last_err:
                        last_err = str(e)
        if self.isInterruptionRequested():
            return
        if not nodes:
            self.failed.emit(last_err or "未能获取该包裹的物流详情")
            return
        nodes = sort_trace_desc(nodes)
        self.ready.emit(nodes)


# ---------------------------------------------------------------
# 时间线条目
# ---------------------------------------------------------------
class _Rail(QWidget):
    def __init__(self, is_first: bool, is_last: bool, parent=None):
        super().__init__(parent)
        self.is_first = is_first
        self.is_last = is_last
        self.setFixedWidth(28)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        dot_y = 14
        pen = QPen(QColor(0, 212, 255, 90), 2)
        p.setPen(pen)
        if not self.is_first:
            p.drawLine(w // 2, 0, w // 2, dot_y)
        if not self.is_last:
            p.drawLine(w // 2, dot_y, w // 2, self.height())
        if self.is_first:
            p.setBrush(QColor(COLOR_ACCENT))
            p.setPen(QPen(QColor(255, 255, 255), 2))
            p.drawEllipse(w // 2 - 6, dot_y - 6, 12, 12)
        else:
            p.setBrush(QColor(26, 34, 58))
            p.setPen(QPen(QColor(0, 212, 255, 120), 2))
            p.drawEllipse(w // 2 - 5, dot_y - 5, 10, 10)
        p.end()


class _TimelineItem(QFrame):
    def __init__(self, node: TraceNode, is_first: bool, is_last: bool, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        rail = _Rail(is_first, is_last)
        lay.addWidget(rail, 0, Qt.AlignmentFlag.AlignTop)

        body = QVBoxLayout()
        body.setSpacing(3)
        head = QHBoxLayout()
        head.setSpacing(8)
        t = QLabel(node.time or "--")
        tf = QFont("YouYuan", 13)
        tf.setWeight(QFont.Weight.DemiBold)
        t.setFont(tf)
        if is_first:
            t.setObjectName("TxtAccent")
        t.setStyleSheet("font-size: 13px;")
        head.addWidget(t)
        head.addStretch(1)
        if is_first:
            pill = QLabel("最新")
            pill.setStyleSheet(
                f"background: rgba(0,212,255,0.16); color: #7DE8FF;"
                f"border-radius: 8px; padding: 2px 10px; font-size: 11px; font-weight: 600;")
            head.addWidget(pill)
        body.addLayout(head)
        s = QLabel(node.status or "")
        s.setWordWrap(True)
        s.setStyleSheet("font-size: 14px;")
        body.addWidget(s)
        if node.location:
            loc = QLabel("📍 " + node.location)
            loc.setObjectName("TxtSub")
            loc.setStyleSheet("font-size: 12px;")
            body.addWidget(loc)
        body.addStretch(1)
        lay.addLayout(body, 1)


# ---------------------------------------------------------------
# 详情弹窗（时间线视图，半宽窗口）
# ---------------------------------------------------------------
class DetailDialog(QDialog):
    def __init__(self, package: Package, config: Config, parent=None):
        super().__init__(parent)
        self.package = package
        self.config = config
        self._worker: DetailWorker | None = None
        self.setWindowTitle("包裹详情")
        self.resize(560, 640)
        self.setMinimumSize(480, 480)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        # ---------- 头部（玻璃卡片） ----------
        head = QFrame()
        head.setObjectName("SurfCard")
        hl = QHBoxLayout(head)
        hl.setContentsMargins(16, 14, 16, 14)
        hl.setSpacing(14)
        badge = QLabel()
        badge.setPixmap(company_badge(package.company_code, 42))
        badge.setFixedSize(42, 42)
        hl.addWidget(badge)
        info = QVBoxLayout()
        info.setSpacing(2)
        name = QLabel(package.company_name)
        f = QFont("YouYuan", 16)
        f.setWeight(QFont.Weight.DemiBold)
        name.setFont(f)
        info.addWidget(name)
        no = QLabel("运单号：" + package.mail_no)
        no.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        no.setObjectName("TxtSub")
        no.setStyleSheet("font-size: 12px;")
        info.addWidget(no)
        hl.addLayout(info, 1)
        chip = QLabel(_STATE_TEXT.get(package.state, "运输中"))
        chip.setProperty("chip", state_chip_key(package.state))
        hl.addWidget(chip, 0, Qt.AlignmentFlag.AlignTop)
        self._state_label = QLabel("")
        self._state_label.setObjectName("TxtSuccess")
        self._state_label.setStyleSheet("font-size: 12px;")
        hl.addWidget(self._state_label, 0, Qt.AlignmentFlag.AlignTop)
        root.addWidget(head)

        # ---------- 时间线 ----------
        panel = QFrame()
        panel.setObjectName("SurfCard")
        ll = QVBoxLayout(panel)
        ll.setContentsMargins(14, 14, 14, 12)
        title = QLabel("物流时间线")
        tf = QFont("YouYuan", 15)
        tf.setWeight(QFont.Weight.DemiBold)
        title.setFont(tf)
        ll.addWidget(title)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._timeline_box = QWidget()
        self._timeline_layout = QVBoxLayout(self._timeline_box)
        self._timeline_layout.setContentsMargins(4, 6, 8, 6)
        self._timeline_layout.setSpacing(0)
        self._timeline_layout.addStretch(1)
        self._scroll.setWidget(self._timeline_box)
        ll.addWidget(self._scroll, 1)
        self._loading = QLabel("正在加载物流轨迹…")
        self._loading.setObjectName("TxtSub")
        ll.addWidget(self._loading)
        root.addWidget(panel, 1)

        # ---------- 底部操作 ----------
        foot = QHBoxLayout()
        foot.addStretch(1)
        copy_btn = QPushButton("复制运单号")
        copy_btn.setObjectName("SurfText")
        copy_btn.clicked.connect(self._copy_mail_no)
        foot.addWidget(copy_btn)
        refresh_btn = QPushButton("刷新详情")
        refresh_btn.setObjectName("SurfText")
        refresh_btn.clicked.connect(lambda: self._start_load())
        foot.addWidget(refresh_btn)
        if package.detail_url:
            web_btn = QPushButton("浏览器查看")
            web_btn.setObjectName("SurfText")
            web_btn.clicked.connect(lambda: webbrowser.open(package.detail_url))
            foot.addWidget(web_btn)
        close_btn = QPushButton("关闭")
        close_btn.setObjectName("SurfFilled")
        close_btn.clicked.connect(self.accept)
        foot.addWidget(close_btn)
        root.addLayout(foot)

        self._start_load()

    # ---------------------------------------------------------------
    def _start_load(self) -> None:
        if self._worker and self._worker.isRunning():
            return
        self._loading.setText("正在加载物流轨迹…")
        while self._timeline_layout.count() > 1:
            item = self._timeline_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if self._worker:
            self._worker.deleteLater()
        self._worker = DetailWorker(self.package, self.config, self)
        self._worker.ready.connect(self._on_ready)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_ready(self, nodes) -> None:
        self._loading.setText(f"共 {len(nodes)} 条物流记录")
        for i, node in enumerate(nodes):
            item = _TimelineItem(node, is_first=(i == 0), is_last=(i == len(nodes) - 1))
            self._timeline_layout.insertWidget(self._timeline_layout.count() - 1, item)

    def _on_failed(self, msg: str) -> None:
        self._loading.setText("加载失败")
        QMessageBox.warning(self, "获取详情失败", msg)

    def closeEvent(self, event) -> None:
        """关闭：非阻塞——抓取线程分离到后台自然结束"""
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()
            from ..core.workers import detach_thread
            detach_thread(self._worker)
            self._worker = None
        super().closeEvent(event)

    def _copy_mail_no(self) -> None:
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.package.mail_no)
        self._state_label.setText("运单号已复制 ✓")
