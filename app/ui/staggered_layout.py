# -*- coding: utf-8 -*-
"""砖墙式错位布局（行与行之间错位）
- 卡片统一大小；奇数行整体右移半卡宽度（行间错位）
- 奇数行起始处的空位自然留空，不填充
"""
from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QLayoutItem, QWidget


class StaggeredLayout(QLayout):
    def __init__(self, parent: QWidget | None = None,
                 margin: int = 20, h_spacing: int = 16, v_spacing: int = 16,
                 offset_ratio: float = 0.5):
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._h = h_spacing
        self._v = v_spacing
        self._offset = offset_ratio
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item: QLayoutItem) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        m = self.contentsMargins()
        effective = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        if not self._items:
            return 0
        w = self._items[0].sizeHint().width()
        h = self._items[0].sizeHint().height()
        gap = self._h
        vgap = self._v
        # 每行可用宽度（首行用满，不预留错位）
        avail = effective.width()
        per_row = max(1, avail // (w + gap)) if avail > 0 else 1
        # 奇数行错位：偏移不能大到让奇数行放不下 per_row 张卡
        # 约束：offset + (per_row-1)*(w+gap) + w <= avail
        offset_max = avail - (per_row * (w + gap) - gap)
        offset = int(w * self._offset)
        if offset > offset_max:
            offset = max(0, offset_max)
        row = 0
        col = 0
        for i, item in enumerate(self._items):
            if col >= per_row:
                col = 0
                row += 1
            x = effective.x() + (offset if row % 2 else 0) + col * (w + gap)
            y = effective.y() + row * (h + vgap)
            if not test_only:
                item.setGeometry(QRect(x, y, w, h))
            col += 1
        return effective.y() + (row + 1) * (h + vgap) - rect.y() + m.bottom()
