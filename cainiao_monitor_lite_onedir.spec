# -*- mode: python ; coding: utf-8 -*-
# 精简版【目录版】打包配置（无 QtWebEngine，运行零解压）
# 用法：pyinstaller --clean --noconfirm cainiao_monitor_lite_onedir.spec
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
              'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
              'PySide6.QtWebEngineQuick', 'PySide6.QtQuick', 'PySide6.QtQml'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CainiaoMonitorLite',
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon='resources/icon.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='CainiaoMonitorLite',
)
