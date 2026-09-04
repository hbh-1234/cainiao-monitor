# -*- coding: utf-8 -*-
"""Surfboard 风格主题（令牌化：深色/浅色 + 强调色可配置）
- 通过主题令牌字典生成 QSS，支持运行时切换深浅色与强调色
- 组件：TopBar / BottomNav / Card / Filled·Tonal·Outlined·Text 按钮 /
  FAB / Chip / Snackbar / Primary Tabs / 玻璃输入框 / 灵动岛按钮配色
"""
from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QWidget

# ---------------------------------------------------------------
# 主题令牌
# ---------------------------------------------------------------
def system_dark_mode() -> bool:
    """跟随系统：读取 Windows 深浅色设置（AppsUseLightTheme，0=深色）"""
    try:
        import winreg
        with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            v, _ = winreg.QueryValueEx(k, "AppsUseLightTheme")
            return int(v) == 0
    except Exception:
        return True   # 读不到默认深色


def resolve_mode(mode: str) -> str:
    """'system' -> 实际深/浅；否则原样返回"""
    if mode == "system":
        return "dark" if system_dark_mode() else "light"
    return mode if mode in ("dark", "light") else "dark"


# ---------------------------------------------------------------
# 配色方案表（用户提供的 8 套浅色系配色，主/次/三级色）
# 第 1 套为当前选中/默认；两色方案第三色沿用第二色
# ---------------------------------------------------------------
COLOR_SCHEMES: dict[str, tuple[str, str, str]] = {
    "浅蓝灰·紫粉": ("#B5C5D7", "#D4B5D7", "#E8E7E9"),      # 第1张 当前选中
    "暖米沙·豆沙绿": ("#EBD7C6", "#D2D7B8", "#EEC8C4"),    # 第2张
    "天蓝·柔粉": ("#8DC5F2", "#EAB2E6", "#F0F5CA"),        # 第3张
    "抹茶绿·米白": ("#DFE691", "#F3F1DA", "#FFFFFF"),      # 第4张
    "冷蓝灰·浅灰": ("#B4C1D4", "#CFD3DD", "#CFD3DD"),      # 第5张
    "薄荷绿·黄绿": ("#ABEBC7", "#CAEBC7", "#FFFFFF"),      # 第6张
    "奶油米·肉粉": ("#F5EAD7", "#F5D7D8", "#F5D7D8"),      # 第7张
    "淡紫丁香·浅粉": ("#D7CDF5", "#F5CDF0", "#F5CDF0"),    # 第8张
}
SCHEME_ORDER = list(COLOR_SCHEMES.keys())


def scheme_colors(name: str) -> tuple[str, str, str]:
    """按方案名取三色；未知方案回退到第 1 张（浅蓝灰·紫粉）"""
    return COLOR_SCHEMES.get(name) or COLOR_SCHEMES[SCHEME_ORDER[0]]


def _blend(c1: QColor, c2: QColor, t: float) -> QColor:
    """按比例混合两个颜色（t=0 全 c1，t=1 全 c2）"""
    return QColor(
        int(c1.red() + (c2.red() - c1.red()) * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue() + (c2.blue() - c1.blue()) * t),
    )


def _build_tokens(mode: str, accent: str,
                  accent2: str | None = None,
                  accent3: str | None = None) -> dict:
    """主题令牌：由所选配色方案（主/次/三级色）派生整站配色
    （FClash 风格：背景渐变、玻璃卡片、面板全部跟随方案色，而非仅字/按钮）"""
    a = QColor(accent)
    b2 = QColor(accent2) if accent2 else QColor(accent).darker(118)
    b3 = QColor(accent3) if accent3 else QColor(accent).lighter(140)
    lum = 0.299 * a.red() + 0.587 * a.green() + 0.114 * a.blue()
    on_accent = "#10151F" if lum > 150 else "#FFFFFF"

    def rgb(c: QColor, alpha: float) -> str:
        return "rgba(%d,%d,%d,%s)" % (c.red(), c.green(), c.blue(),
                                      ("%g" % alpha))

    if mode == "light":
        base_top = QColor("#F4F6FB")
        base_bot = QColor("#E7EBF4")
        bg_top = _blend(base_top, a, 0.32).name()
        bg_bot = _blend(base_bot, b3, 0.26).name()
        soft = a.darker(118).name()          # 浅色下强调色文字需偏深
        deep = a.darker(118).name()
        chip_bg = rgb(a, 0.16)
        chip_fg = deep
        focus_bg = rgb(a, 0.10)
        menu_sel = rgb(a, 0.16)
        card_tint = _blend(QColor(255, 255, 255), b2, 0.30)
        glass_tint = _blend(QColor(255, 255, 255), a, 0.18)
        nav_tint = _blend(QColor(255, 255, 255), b3, 0.22)
        return {
            "BG_TOP": bg_top, "BG_BOTTOM": bg_bot,
            "ACCENT": accent, "ACCENT_BLUE": b2.name(), "TERTIARY": b3.name(),
            "ACCENT_SOFT": soft, "ON_ACCENT": on_accent,
            "GLASS": rgb(glass_tint, 0.72), "GLASS_BORDER": rgb(card_tint, 0.95),
            "GLASS_STRONG": rgb(card_tint, 0.94),
            "TEXT": "#1A1B20", "TEXT_SUB": "#565B66",
            "OUTLINE": "rgba(26,27,32,0.28)",
            "CHIP_BG": chip_bg, "CHIP_FG": chip_fg,
            "CHIP_CYAN_BG": chip_bg, "CHIP_CYAN_FG": chip_fg,
            "CHIP_ORANGE_BG": "rgba(251,191,36,0.18)", "CHIP_ORANGE_FG": "#8A5300",
            "CHIP_GREEN_BG": "rgba(52,211,153,0.18)", "CHIP_GREEN_FG": "#005C3B",
            "CHIP_RED_BG": "rgba(248,113,113,0.18)", "CHIP_RED_FG": "#B42318",
            "SUCCESS_FG": "#007A54",
            "CARD_BG": rgb(card_tint, 0.85), "CARD_BORDER": rgb(card_tint, 1.0),
            "HOVER": "rgba(26,27,32,0.06)", "PRESS": "rgba(26,27,32,0.10)",
            "INPUT_BG": "rgba(255,255,255,0.85)", "INPUT_BORDER": "rgba(26,27,32,0.22)",
            "FOCUS_BG": focus_bg,
            "SCROLL": "rgba(26,27,32,0.25)", "SCROLL_HOVER": "rgba(26,27,32,0.45)",
            "MENU_BG": rgb(card_tint, 0.97), "MENU_SEL": menu_sel,
            "DIVIDER": "rgba(26,27,32,0.12)",
            "SNACK_BG": "rgba(38,42,52,0.96)", "SNACK_FG": "#F0F0F7",
            "ERR_BG": "rgba(248,113,113,0.18)", "ERR_FG": "#B42318",
            "NAV_BG": rgb(nav_tint, 0.92), "TOP_BG": rgb(glass_tint, 0.92),
            "BASE": "#FFFFFF",
        }
    # 深色（默认）：深海军蓝底 + 方案色染色（FClash 风格）
    base_top = QColor("#0A1122")
    base_bot = QColor("#0E1A33")
    bg_top = _blend(base_top, a, 0.20).name()
    bg_bot = _blend(base_bot, b3, 0.16).name()
    soft = a.lighter(155).name()
    chip_bg = rgb(a, 0.16)
    chip_fg = soft
    focus_bg = rgb(a, 0.08)
    menu_sel = rgb(a, 0.14)
    card_tint = _blend(QColor(255, 255, 255), b2, 0.38)
    glass_tint = _blend(QColor(255, 255, 255), a, 0.10)
    nav_tint = _blend(QColor(13, 20, 38), b3, 0.10)
    top_tint = _blend(QColor(10, 17, 34), a, 0.10)
    strong_tint = _blend(QColor(20, 28, 48), b2, 0.14)
    return {
        "BG_TOP": bg_top, "BG_BOTTOM": bg_bot,
        "ACCENT": accent, "ACCENT_BLUE": b2.name(), "TERTIARY": b3.name(),
        "ACCENT_SOFT": soft, "ON_ACCENT": on_accent,
        "GLASS": rgb(glass_tint, 0.10), "GLASS_BORDER": rgb(card_tint, 0.30),
        "GLASS_STRONG": rgb(strong_tint, 0.94),
        "TEXT": "#E9F1FF", "TEXT_SUB": "#8A97B5",
        "OUTLINE": "rgba(255,255,255,0.16)",
        "CHIP_BG": chip_bg, "CHIP_FG": chip_fg,
        "CHIP_CYAN_BG": chip_bg, "CHIP_CYAN_FG": chip_fg,
        "CHIP_ORANGE_BG": "rgba(251,191,36,0.14)", "CHIP_ORANGE_FG": "#FFD58A",
        "CHIP_GREEN_BG": "rgba(52,211,153,0.14)", "CHIP_GREEN_FG": "#8AF0C8",
        "CHIP_RED_BG": "rgba(248,113,113,0.16)", "CHIP_RED_FG": "#FFA8A8",
        "SUCCESS_FG": "#34D399",
        "CARD_BG": rgb(card_tint, 0.09), "CARD_BORDER": rgb(card_tint, 0.32),
        "HOVER": "rgba(255,255,255,0.08)", "PRESS": "rgba(255,255,255,0.12)",
        "INPUT_BG": "rgba(255,255,255,0.06)", "INPUT_BORDER": "rgba(255,255,255,0.16)",
        "FOCUS_BG": focus_bg,
        "SCROLL": "rgba(255,255,255,0.18)", "SCROLL_HOVER": "rgba(255,255,255,0.30)",
        "MENU_BG": rgb(strong_tint, 0.98), "MENU_SEL": menu_sel,
        "DIVIDER": "rgba(255,255,255,0.10)",
        "SNACK_BG": "rgba(22,30,52,0.96)", "SNACK_FG": "#E9F1FF",
        "ERR_BG": "rgba(60,20,24,0.96)", "ERR_FG": "#FFB4B4",
        "NAV_BG": rgb(nav_tint, 0.95), "TOP_BG": rgb(top_tint, 0.88),
        "BASE": _blend(base_bot, b3, 0.10).name(),
    }


def _build_qss(t: dict) -> str:
    return f"""
* {{
    font-family: "YouYuan", "幼圆", "Microsoft YaHei UI", "Microsoft YaHei",
                 "Segoe UI", Roboto, sans-serif;
    outline: none;
}}
QWidget {{ color: {t['TEXT']}; font-size: 14px; }}
QToolTip {{
    background: {t['GLASS_STRONG']}; color: {t['TEXT']};
    border: 1px solid {t['GLASS_BORDER']}; border-radius: 8px;
    padding: 6px 10px; font-size: 12px;
}}

QFrame#SurfCard {{
    background: {t['CARD_BG']}; border: 1px solid {t['CARD_BORDER']}; border-radius: 18px;
}}
QFrame#SurfCardFlat {{
    background: {t['GLASS']}; border: 1px solid {t['GLASS_BORDER']}; border-radius: 14px;
}}
QFrame#SurfDialogCard {{
    background: {t['GLASS_STRONG']}; border: 1px solid {t['GLASS_BORDER']}; border-radius: 24px;
}}
QFrame#SurfTopBar {{ background: {t['TOP_BG']}; border-bottom: 1px solid {t['DIVIDER']}; }}
QFrame#SurfBottomNav {{ background: {t['NAV_BG']}; border-top: 1px solid {t['DIVIDER']}; }}
QLabel#SurfTopTitle {{ font-size: 19px; font-weight: 700; color: {t['TEXT']}; }}
QLabel#SurfTopSub {{ font-size: 11px; color: {t['TEXT_SUB']}; }}

QPushButton#SurfFilled {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {t['ACCENT']}, stop:1 {t['ACCENT_BLUE']});
    color: {t['ON_ACCENT']}; border: none; border-radius: 16px;
    padding: 10px 26px; font-weight: 700; font-size: 14px;
}}
QPushButton#SurfFilled:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {QColor(t['ACCENT']).lighter(112).name()},
                stop:1 {QColor(t['ACCENT_BLUE']).lighter(112).name()});
}}
QPushButton#SurfFilled:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {QColor(t['ACCENT']).darker(110).name()},
                stop:1 {QColor(t['ACCENT_BLUE']).darker(110).name()});
}}
QPushButton#SurfFilled:disabled {{
    background: {t['HOVER']}; color: {t['TEXT_SUB']};
}}

QPushButton#SurfTonal {{
    background: {t['CHIP_BG']}; color: {t['CHIP_FG']};
    border: none; border-radius: 16px; padding: 10px 26px; font-weight: 600; font-size: 14px;
}}
QPushButton#SurfTonal:hover {{ background: {t['CHIP_BG']}; border: 1px solid {t['ACCENT']}; }}
QPushButton#SurfTonal:pressed {{ background: {t['PRESS']}; }}

QPushButton#SurfOutlined {{
    background: transparent; color: {t['CHIP_FG']};
    border: 1px solid {t['OUTLINE']}; border-radius: 16px;
    padding: 9px 25px; font-weight: 600; font-size: 14px;
}}
QPushButton#SurfOutlined:hover {{ background: {t['HOVER']}; }}

QPushButton#SurfText {{
    background: transparent; color: {t['CHIP_FG']};
    border: none; border-radius: 16px; padding: 8px 18px; font-weight: 600; font-size: 14px;
}}
QPushButton#SurfText:hover {{ background: {t['HOVER']}; }}

QPushButton#SurfIcon, QToolButton#SurfIcon {{
    background: transparent; border: none; border-radius: 18px;
    color: {t['TEXT']};
}}
QPushButton#SurfIcon:hover, QToolButton#SurfIcon:hover {{ background: {t['HOVER']}; }}
QPushButton#SurfIcon:pressed, QToolButton#SurfIcon:pressed {{ background: {t['PRESS']}; }}

QPushButton#SurfNavItem {{
    background: transparent; border: 1px solid transparent; border-radius: 10px;
    color: {t['TEXT_SUB']}; padding: 6px 10px; font-size: 12px; font-weight: 600;
}}
QPushButton#SurfNavItem:hover {{ background: {t['HOVER']}; color: {t['TEXT']}; }}
QPushButton#SurfNavItem:checked {{
    background: {t['CHIP_BG']}; color: {t['CHIP_FG']};
    border: 2px solid {t['ACCENT']};
}}

QLabel#SurfChip {{
    border-radius: 10px; padding: 4px 12px; font-size: 12px; font-weight: 600;
}}

/* 文本角色（主题切换时颜色自动跟随） */
QLabel#TxtMain {{ color: {t['TEXT']}; }}
QLabel#TxtSub {{ color: {t['TEXT_SUB']}; }}
QLabel#TxtAccent {{ color: {t['CHIP_FG']}; }}
QLabel#TxtError {{ color: {t['ERR_FG']}; }}
QLabel#TxtSuccess {{ color: {t['SUCCESS_FG']}; }}

/* 设置滑层：整窗背景跟随主题；子页抽屉不透明（盖在主设置页上） */
QWidget#SettingsRoot {{ background: {t['BG_TOP']}; }}
QWidget#SettingsPage {{ background: {t['BG_TOP']}; }}
QDialog#SurfDialog {{ background: {t['BG_TOP']}; }}

/* 状态 Chip（属性驱动，主题切换时自动跟随） */
QLabel[chip="cyan"] {{
    background: {t['CHIP_CYAN_BG']}; color: {t['CHIP_CYAN_FG']};
    border-radius: 10px; padding: 4px 12px; font-size: 12px; font-weight: 600;
}}
QLabel[chip="orange"] {{
    background: {t['CHIP_ORANGE_BG']}; color: {t['CHIP_ORANGE_FG']};
    border-radius: 10px; padding: 4px 12px; font-size: 12px; font-weight: 600;
}}
QLabel[chip="green"] {{
    background: {t['CHIP_GREEN_BG']}; color: {t['CHIP_GREEN_FG']};
    border-radius: 10px; padding: 4px 12px; font-size: 12px; font-weight: 600;
}}
QLabel[chip="red"] {{
    background: {t['CHIP_RED_BG']}; color: {t['CHIP_RED_FG']};
    border-radius: 10px; padding: 4px 12px; font-size: 12px; font-weight: 600;
}}

QLineEdit, QTextEdit {{
    background: {t['INPUT_BG']}; border: 1px solid {t['INPUT_BORDER']};
    border-radius: 12px; padding: 10px 14px; color: {t['TEXT']};
    selection-background-color: {t['ACCENT']}; selection-color: {t['ON_ACCENT']};
}}
QComboBox {{
    background: {t['INPUT_BG']}; border: 1px solid {t['INPUT_BORDER']};
    border-radius: 12px; padding-left: 14px; min-height: 34px; color: {t['TEXT']};
    selection-background-color: {t['ACCENT']}; selection-color: {t['ON_ACCENT']};
}}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
    border: 1px solid {t['ACCENT']}; background: {t['FOCUS_BG']};
}}
QLineEdit:disabled, QTextEdit:disabled {{
    border-color: {t['DIVIDER']}; color: {t['TEXT_SUB']};
}}
QComboBox::drop-down {{ border: none; width: 30px; }}
QComboBox::down-arrow {{
    image: none;
    width: 10px; height: 6px;
    border-left: 5px solid transparent; border-right: 5px solid transparent;
    border-top: 6px solid {t['TEXT_SUB']}; margin-right: 10px;
}}
QComboBox QAbstractItemView {{
    background: {t['MENU_BG']}; border: 1px solid {t['GLASS_BORDER']};
    border-radius: 10px; selection-background-color: {t['MENU_SEL']};
    selection-color: {t['TEXT']}; padding: 4px;
}}

QTabWidget::pane {{ border: none; background: transparent; top: 0; }}
QTabBar::tab {{
    background: transparent; color: {t['TEXT_SUB']};
    padding: 12px 22px; font-size: 14px; font-weight: 600;
    border-bottom: 3px solid transparent;
}}
QTabBar::tab:selected {{ color: {t['CHIP_FG']}; border-bottom: 3px solid {t['ACCENT']}; }}
QTabBar::tab:hover {{ color: {t['CHIP_FG']}; }}

QMenu {{
    background: {t['MENU_BG']}; border: 1px solid {t['GLASS_BORDER']};
    border-radius: 10px; padding: 6px;
}}
QMenu::item {{ padding: 10px 28px 10px 16px; border-radius: 6px; color: {t['TEXT']}; }}
QMenu::item:selected {{ background: {t['MENU_SEL']}; color: {t['TEXT']}; }}
QMenu::separator {{ height: 1px; background: {t['DIVIDER']}; margin: 6px 10px; }}

QFrame#SurfSnackbar {{
    background: {t['SNACK_BG']}; border: 1px solid {t['GLASS_BORDER']}; border-radius: 12px;
}}
QFrame#SurfSnackbar QLabel {{ color: {t['SNACK_FG']}; font-size: 14px; }}
QFrame#SurfSnackbar[state="error"] {{
    background: {t['ERR_BG']}; border: 1px solid rgba(248,113,113,0.4);
}}
QFrame#SurfSnackbar[state="error"] QLabel {{ color: {t['ERR_FG']}; }}

QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{
    background: transparent; width: 8px; margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {t['SCROLL']}; border-radius: 4px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {t['SCROLL_HOVER']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{
    background: transparent; height: 8px; margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {t['SCROLL']}; border-radius: 4px; min-width: 30px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QDialog {{ background: {t['BG_TOP']}; }}
QMessageBox {{ background: {t['BG_TOP']}; }}
QMessageBox QLabel {{ color: {t['TEXT']}; font-size: 14px; }}
QMessageBox QPushButton {{
    background: {t['CHIP_BG']}; color: {t['CHIP_FG']};
    border: none; border-radius: 14px; padding: 8px 22px; min-width: 70px; font-weight: 600;
}}
QMessageBox QPushButton:hover {{ background: {t['MENU_SEL']}; }}
"""


CURRENT: dict = _build_tokens("dark", "#00D4FF")


def tk(key: str) -> str:
    """读取当前主题令牌（供绘制/自绘控件使用，切换主题后自动更新）"""
    return CURRENT.get(key, "")


def apply_theme(app: QApplication, mode: str = "dark", accent: str = "#00D4FF",
                 accent2: str | None = None, accent3: str | None = None) -> None:
    """应用主题：深浅色 + 配色方案（主/次/三级色）"""
    global CURRENT
    t = _build_tokens(mode, accent, accent2, accent3)
    CURRENT = t
    app.setStyleSheet(_build_qss(t))
    app.setFont(QFont("YouYuan", 10))
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(t["BG_TOP"]))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(t["TEXT"]))
    pal.setColor(QPalette.ColorRole.Base, QColor(t["BASE"]))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(t["GLASS_STRONG"]))
    pal.setColor(QPalette.ColorRole.Text, QColor(t["TEXT"]))
    pal.setColor(QPalette.ColorRole.Button, QColor(t["GLASS_STRONG"]))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(t["TEXT"]))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(t["ACCENT"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(t["ON_ACCENT"]))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(t["GLASS_STRONG"]))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(t["TEXT"]))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(t["TEXT_SUB"]))
    pal.setColor(QPalette.ColorRole.Link, QColor(t["ACCENT"]))
    app.setPalette(pal)


def repolish_all(app: QApplication) -> None:
    """运行时切换主题后，刷新所有窗口及其全部子控件的样式
    （仅顶层控件不会刷新子标签/按钮的颜色，必须递归）"""
    for w in app.topLevelWidgets():
        for c in ([w] + w.findChildren(QWidget)):
            try:
                c.style().unpolish(c)
                c.style().polish(c)
                c.update()
            except Exception:
                pass


def surf_shadow(widget: QWidget, glow: bool = False) -> QGraphicsDropShadowEffect:
    effect = QGraphicsDropShadowEffect(widget)
    if glow:
        effect.setBlurRadius(28)
        effect.setOffset(0, 4)
        effect.setColor(QColor(0, 212, 255, 70))
    else:
        effect.setBlurRadius(20)
        effect.setOffset(0, 4)
        effect.setColor(QColor(0, 0, 0, 110))
    widget.setGraphicsEffect(effect)
    return effect


def chip_style(bg: str, fg: str) -> str:
    return (f"background: {bg}; color: {fg}; border-radius: 10px;"
            f"padding: 4px 12px; font-size: 12px; font-weight: 600;")
