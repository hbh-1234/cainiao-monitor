# -*- mode: python ; coding: utf-8 -*-
# 完整版【目录版】打包配置：DLL 直接放在 exe 旁，运行零解压，
# 彻底规避单文件模式 "Failed to extract MSVCP140.dll: Permission denied" 问题
# 用法：pyinstaller --clean --noconfirm cainiao_monitor_full_onedir.spec
from PyInstaller.utils.hooks import collect_all, collect_data_files

datas, binaries, hiddenimports = [], [], []

for m in ["PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineCore",
          "PySide6.QtWebEngineQuick", "PySide6.QtQuick", "PySide6.QtQml"]:
    d, b, h = collect_all(m)
    datas += d; binaries += b; hiddenimports += h

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
    [],
    exclude_binaries=True,
    name='CainiaoMonitor',
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
    name='CainiaoMonitor',
)
