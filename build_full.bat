@echo off
rem ============================================================
rem  打包完整版【目录版】（推荐）—— 运行零解压，
rem  彻底规避 "Failed to extract MSVCP140.dll: Permission denied"
rem  产物：dist_full\CainiaoMonitor\CainiaoMonitor.exe（双击即用）
rem  如需传统单文件版：build_full_onefile.bat
rem ============================================================
cd /d %~dp0

echo [1/3] 安装依赖（首次较慢）...
python -m pip install -r requirements-dev.txt || goto :err

echo [2/3] 生成应用图标...
python tools\gen_icon.py || goto :err

echo [3/3] PyInstaller 打包中（完整版体积较大，请耐心等待）...
python -m PyInstaller --clean --noconfirm --distpath dist_full --workpath build_full cainiao_monitor_full_onedir.spec || goto :err

echo.
echo 打包完成！程序位于：dist_full\CainiaoMonitor\CainiaoMonitor.exe
pause
exit /b 0

:err
echo.
echo 打包失败，请检查上方错误信息。
pause
exit /b 1
