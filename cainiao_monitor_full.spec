# -*- mode: python ; coding: utf-8 -*-
# 完整版打包配置：包含 QtWebEngine（内嵌浏览器登录）
# 用法：pyinstaller --clean --noconfirm cainiao_monitor_full.spec
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

datas, binaries, hiddenimports = [], [], []

# WebEngine 相关模块（收集其二进制与资源）
for m in ["PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineCore",
          "PySide6.QtWebEngineQuick", "PySide6.QtQuick", "PySide6.QtQml"]:
    d, b, h = collect_all(m)
    datas += d; binaries += b; hiddenimports += h

# Qt 翻译文件（让按钮等显示中文）
try:
    datas += collect_data_files("PySide6", includes=["translations/*.qm"])
except Exception:
    pass

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas', 'PIL',
              'PyQt5', 'PyQt6', 'PySide2'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CainiaoMonitor_SingleFile',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                 # WebEngine 大文件建议关闭 UPX，避免被杀毒误报
    console=False,             # 无控制台窗口
    disable_windowed_traceback=False,
    icon='resources/icon.ico',
    uac_admin=False,
)
