@echo off
rem ============================================================
rem  打包完整版【单文件版】（可选）
rem  注意：单文件启动时会把 DLL 解压到系统临时目录，
rem  若被杀软/权限策略拦截会报 "Failed to extract MSVCP140.dll:
rem  Permission denied"，建议改用 build_full.bat 目录版。
rem  产物：dist_onefile\CainiaoMonitor_SingleFile.exe
rem ============================================================
cd /d %~dp0
python -m pip install -r requirements-dev.txt || goto :err
python tools\gen_icon.py || goto :err
python -m PyInstaller --clean --noconfirm --distpath dist_onefile --workpath build_onefile cainiao_monitor_full.spec || goto :err
echo.
echo 打包完成！程序位于：dist_onefile\CainiaoMonitor_SingleFile.exe
pause
exit /b 0
:err
echo.
echo 打包失败，请检查上方错误信息。
pause
exit /b 1
