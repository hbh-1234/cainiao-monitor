# -*- mode: python ; coding: utf-8 -*-
# 精简版打包配置：不包含 QtWebEngine，体积更小（登录改为“浏览器 + 粘贴 Cookie”）
# 用法：pyinstaller --clean --noconfirm cainiao_monitor_lite.spec
from PyInstaller.utils.hooks import collect_data_files

datas = []
try:
    datas += collect_data_files("PySide6", includes=["translations/*.qm"])
except Exception:
    pass

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['requests'],
    hookspath=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas', 'PIL',
              'PyQt5', 'PyQt6', 'PySide2',
              # 排除 WebEngine，运行时自动降级为“粘贴 Cookie”登录
              'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
              'PySide6.QtWebEngineQuick', 'PySide6.QtQuick', 'PySide6.QtQml'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CainiaoMonitorLite_SingleFile',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon='resources/icon.ico',
    uac_admin=False,
)
