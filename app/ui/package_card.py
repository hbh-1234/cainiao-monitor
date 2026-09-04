# -*- coding: utf-8 -*-
"""包裹卡片 —— Surfboard 风格深色玻璃卡片（主题感知）
- 所有颜色由全局主题(QSS)控制，切换深浅色/强调色后自动跟随
- 状态 Chip 用属性(chip="cyan|orange|green|red")驱动
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QMenu,
                               QSizePolicy, QVBoxLayout, QWidget)

from ..models import Package
from .icons import company_badge
from .theme import surf_shadow

_STATE_TEXT = {"transporting": "运输中", "delivering": "派送中",
               "signed": "已签收", "problem": "异常"}


def state_chip_key(state: str) -> str:
    """状态 → Chip 属性键（青=运输中 / 橙=派送中 / 绿=已签收 / 红=异常）"""
    return {"delivering": "orange", "signed": "green",
            "problem": "red"}.get(state, "cyan")


class PackageCard(QFrame):
    """点击发出 clicked(package) 信号；右键发出 delete_requested(package)"""
    clicked = Signal(object)
    delete_requested = Signal(object)

    CARD_W = 330
    CARD_H = 148

    def __init__(self, package: Package, parent: QWidget | None = None):
        super().__init__(parent)
        self.package = package
        self.setObjectName("SurfCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # 统一大小（错位布局要求）
        self.setFixedSize(self.CARD_W, self.CARD_H)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        # 右键菜单
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self._shadow = surf_shadow(self, glow=False)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 12)
        outer.setSpacing(10)

        # ---- 第一行：头像 + 标题/副标题 + 状态 Chip ----
        top = QHBoxLayout()
        top.setSpacing(12)
        avatar = QLabel()
        avatar.setPixmap(company_badge(package.company_code, 40))
        avatar.setFixedSize(40, 40)
        top.addWidget(avatar)

        info = QVBoxLayout()
        info.setSpacing(2)
        name = QLabel(package.company_name)
        f = QFont("YouYuan", 15)
        f.setWeight(QFont.Weight.DemiBold)
        name.setFont(f)
        info.addWidget(name)
        no = QLabel(package.masked_no())
        no.setObjectName("TxtSub")
        no.setStyleSheet("font-size: 12px;")
        info.addWidget(no)
        top.addLayout(info, 1)

        chip = QLabel(_STATE_TEXT.get(package.state, "运输中"))
        chip.setProperty("chip", state_chip_key(package.state))
        top.addWidget(chip, 0, Qt.AlignmentFlag.AlignTop)
        if package.extra.get("pkg_type") == "寄件":
            tchip = QLabel("寄件")
            tchip.setProperty("chip", "orange")
            top.addWidget(tchip, 0, Qt.AlignmentFlag.AlignTop)
        outer.addLayout(top)

        # ---- 正文：最新状态（最多两行） ----
        status_text = package.latest_status or "暂无物流信息"
        self._status = QLabel(status_text)
        self._status.setWordWrap(True)
        self._status.setMaximumHeight(42)
        self._status.setStyleSheet("font-size: 14px;")
        outer.addWidget(self._status)

        # ---- 底行：时间 + 详情 ----
        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        self._time = QLabel(package.latest_time or "--")
        self._time.setObjectName("TxtSub")
        self._time.setStyleSheet("font-size: 12px;")
        bottom.addWidget(self._time)
        bottom.addStretch(1)
        more = QLabel("详情")
        more.setObjectName("TxtAccent")
        more.setStyleSheet("font-size: 14px; font-weight: 600;")
        bottom.addWidget(more)
        outer.addLayout(bottom)

    # ---------- 交互 ----------
    def _show_context_menu(self, pos: QPoint) -> None:
        menu = QMenu(self)
        act = menu.addAction("删除该运单")
        if menu.exec(self.mapToGlobal(pos)) == act:
            self.delete_requested.emit(self.package)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.package)
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:
        self._shadow.setBlurRadius(30)
        self._shadow.setColor(QColor(0, 212, 255, 60))
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._shadow.setBlurRadius(20)
        self._shadow.setColor(QColor(0, 0, 0, 110))
        super().leaveEvent(event)
