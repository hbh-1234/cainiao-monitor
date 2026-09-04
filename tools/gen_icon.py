# -*- coding: utf-8 -*-
"""生成 resources/icon.ico（应用图标，多尺寸）
用法：python tools/gen_icon.py
说明：使用 PySide6 绘制（打包机已装 PySide6，无需额外安装 Pillow）
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QGuiApplication, QIcon, QLinearGradient,
                           QPainter, QPainterPath, QPixmap)

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "resources", "icon.ico")


def draw_icon(size: int) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r = size * 0.22
    grad = QLinearGradient(0, 0, 0, size)
    grad.setColorAt(0.0, QColor("#5f9bff"))
    grad.setColorAt(1.0, QColor("#2f7bff"))
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), r, r)
    p.fillPath(path, grad)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 255, 255, 60))
    p.drawRoundedRect(QRectF(size*0.07, size*0.05, size*0.86, size*0.36), size*0.16, size*0.16)
    # 包裹盒子
    bw, bh = size * 0.42, size * 0.32
    bx, by = size * 0.29, size * 0.36
    p.setBrush(QColor(255, 255, 255, 235))
    p.setPen(QColor(255, 255, 255, 220))
    p.drawRoundedRect(QRectF(bx, by, bw, bh), size*0.05, size*0.05)
    # 胶带
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#2f7bff"))
    p.drawRect(QRectF(bx + bw*0.44, by, bw*0.12, bh))
    # 动感线
    p.setPen(QColor(255, 255, 255, 210))
    p.setBrush(Qt.BrushStyle.NoBrush)
    for i in range(3):
        y0 = size * 0.40 + i * size * 0.12
        p.drawLine(int(size*0.80), int(y0), int(size*0.92), int(y0))
    p.end()
    return pm


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    app = QGuiApplication(sys.argv[:1])  # 仅需要 GUI 基础
    icon = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(draw_icon(s))
    ok = icon.pixmap(256, 256).save(OUT, "ICO")
    print("icon saved:", OUT, "ok=", ok)


if __name__ == "__main__":
    main()
