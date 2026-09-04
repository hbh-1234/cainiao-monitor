# -*- coding: utf-8 -*-
"""程序化图标（Material Design 3 风格，全部 QPainter 绘制，无外部图片）
- make_app_icon：应用/托盘图标（主色圆角方块 + 白色包裹）
- company_badge：快递公司徽章（品牌色圆角方块 + 简称）
- status_dot：物流状态圆点
- m3_icon：MD3 线型图标（add / refresh / more / close / box）
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QIcon, QLinearGradient, QPainter,
                           QPainterPath, QPen, QPixmap, QRadialGradient)

from ..constants import (COLOR_ERROR, COLOR_OK, COLOR_ON_PRIMARY,
                         COLOR_ON_SURFACE, COLOR_PRIMARY, COLOR_WARN,
                         company_info)

_COLOR_CACHE: dict[str, str] = {}


def _company_color(code: str) -> str:
    if code not in _COLOR_CACHE:
        _COLOR_CACHE[code] = company_info(code)[3]
    return _COLOR_CACHE[code]


def _pix(size: int) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    return pm


# ---------------------------------------------------------------
def make_app_icon(size: int = 64) -> QIcon:
    """应用图标：MD3 主色圆角方块 + 白色包裹图案"""
    pm = _pix(size)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, QColor("#4D72E4"))
    grad.setColorAt(1.0, QColor(COLOR_PRIMARY))
    path = QPainterPath()
    r = size * 0.22
    path.addRoundedRect(QRectF(0, 0, size, size), r, r)
    p.fillPath(path, grad)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 255, 255, 60))
    p.drawRoundedRect(QRectF(size*0.08, size*0.06, size*0.84, size*0.34), size*0.18, size*0.18)
    # 包裹盒子
    bw, bh = size * 0.42, size * 0.34
    bx, by = size * 0.29, size * 0.34
    p.setPen(QPen(QColor(255, 255, 255, 220), size * 0.03))
    p.setBrush(QColor(255, 255, 255, 235))
    p.drawRoundedRect(QRectF(bx, by, bw, bh), size*0.05, size*0.05)
    # 胶带
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(COLOR_PRIMARY))
    p.drawRect(QRectF(bx + bw*0.44, by, bw*0.12, bh))
    # 右侧动感线
    p.setPen(QPen(QColor(255, 255, 255, 210), size * 0.045,
                  Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for i, off in enumerate((0.0, 0.06, 0.12)):
        p.drawLine(QPointF(size*0.78, size*0.4 + i*size*0.11 + off),
                   QPointF(size*0.90, size*0.4 + i*size*0.11 + off))
    p.end()
    return QIcon(pm)


def company_badge(code: str, size: int = 44) -> QPixmap:
    """快递公司徽章：品牌色圆角方块（MD3 头像比例）+ 简称文字"""
    color = QColor(_company_color(code))
    info = company_info(code)
    short = info[2]
    pm = _pix(size)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, color.lighter(112))
    grad.setColorAt(1.0, color)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), size * 0.30, size * 0.30)
    p.fillPath(path, grad)
    f = QFont("YouYuan", max(9, int(size * 0.28)))
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor(255, 255, 255))
    p.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, short)
    p.end()
    return pm


def status_dot(state: str, size: int = 10) -> QPixmap:
    """状态圆点：正常绿 / 派送橙 / 异常红"""
    color = {"signed": COLOR_OK, "delivering": COLOR_WARN,
             "problem": COLOR_ERROR}.get(state, COLOR_PRIMARY)
    pm = _pix(size)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r = QRadialGradient(size/2, size/2, size/2)
    c = QColor(color)
    r.setColorAt(0.0, QColor(c.red(), c.green(), c.blue(), 90))
    r.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(), 0))
    p.setBrush(r)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QRectF(0, 0, size, size))
    p.setBrush(c)
    p.drawEllipse(QRectF(size*0.22, size*0.22, size*0.56, size*0.56))
    p.end()
    return pm


# ---------------------------------------------------------------
# MD3 线型图标
# ---------------------------------------------------------------
def _paint_icon(p: QPainter, kind: str, size: int, color: QColor) -> None:
    """在 size×size 的画笔上绘制图标（坐标按 24dp 网格缩放）"""
    s = size / 24.0
    pen = QPen(color, max(1.8, 2 * s), Qt.PenStyle.SolidLine,
               Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    def pt(x: float, y: float) -> QPointF:
        return QPointF(x * s, y * s)

    if kind == "add":
        p.drawLine(pt(12, 5), pt(12, 19))
        p.drawLine(pt(5, 12), pt(19, 12))
    elif kind == "close":
        p.drawLine(pt(6, 6), pt(18, 18))
        p.drawLine(pt(18, 6), pt(6, 18))
    elif kind == "more":
        p.setBrush(color)
        p.setPen(Qt.PenStyle.NoPen)
        for cx in (7, 12, 17):
            p.drawEllipse(pt(cx, 12), 1.6 * s, 1.6 * s)
    elif kind == "refresh":
        # 带缺口的圆 + 箭头
        r = 7.0
        rect = QRectF((12 - r) * s, (12 - r) * s, 2 * r * s, 2 * r * s)
        p.drawArc(rect, 40 * 16, 280 * 16)   # 缺口约 40°~80°
        # 箭头位于缺口起始端（40°）
        a = math.radians(40)
        x1 = (12 + r * math.cos(a)) * s
        y1 = (12 - r * math.sin(a)) * s
        ta = a + math.pi / 2   # 沿弧切线方向
        L = 3.4 * s
        p.drawLine(QPointF(x1, y1),
                   QPointF(x1 + math.cos(ta) * L, y1 - math.sin(ta) * L))
        p.drawLine(QPointF(x1, y1),
                   QPointF(x1 + math.cos(ta - math.pi/3) * L,
                           y1 - math.sin(ta - math.pi/3) * L))
    elif kind == "box":
        # 包裹盒子（线型）
        p.drawRoundedRect(QRectF(4*s, 6*s, 16*s, 13*s), 2*s, 2*s)
        p.drawLine(pt(4, 10), pt(20, 10))
        p.drawLine(pt(12, 10), pt(12, 6))
    elif kind == "search":
        p.drawEllipse(pt(10, 10), 5.0 * s, 5.0 * s)
        p.drawLine(pt(14, 14), pt(19, 19))
    elif kind == "gear":
        # 齿轮：8 个齿 + 圆环
        for i in range(8):
            a = i * math.pi / 4.0
            x1 = (12 + 6.2 * math.cos(a)) * s
            y1 = (12 - 6.2 * math.sin(a)) * s
            x2 = (12 + 8.4 * math.cos(a)) * s
            y2 = (12 - 8.4 * math.sin(a)) * s
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        p.drawEllipse(pt(12, 12), 4.6 * s, 4.6 * s)
    elif kind == "pin":
        # 位置图钉
        path = QPainterPath()
        path.moveTo(pt(12, 20))
        path.cubicTo(pt(12, 20), pt(5, 14), pt(5, 10))
        path.cubicTo(pt(5, 6), pt(8, 4), pt(12, 4))
        path.cubicTo(pt(16, 4), pt(19, 6), pt(19, 10))
        path.cubicTo(pt(19, 14), pt(12, 20), pt(12, 20))
        p.drawPath(path)
        p.drawEllipse(pt(12, 10), 2.2 * s, 2.2 * s)


def m3_icon(kind: str, size: int = 24, color: str = COLOR_ON_SURFACE) -> QIcon:
    """生成线型图标。kind: add/refresh/more/close/box/search/pin/gear"""
    pm = _pix(size)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    _paint_icon(p, kind, size, QColor(color))
    p.end()
    return QIcon(pm)


def m3_icon_pixmap(kind: str, size: int = 24, color: str = COLOR_ON_SURFACE) -> QPixmap:
    """生成 MD3 线型图标像素图（用于 QLabel.setPixmap）"""
    return m3_icon(kind, size, color).pixmap(size, size)
