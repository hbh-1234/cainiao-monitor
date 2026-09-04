@echo off
rem ============================================================
rem  打包精简版【单文件版】（可选），注意事项同上
rem  产物：dist_onefile_lite\CainiaoMonitorLite_SingleFile.exe
rem ============================================================
cd /d %~dp0
python -m pip install -r requirements-dev.txt || goto :err
python tools\gen_icon.py || goto :err
python -m PyInstaller --clean --noconfirm --distpath dist_onefile_lite --workpath build_onefile_lite cainiao_monitor_lite.spec || goto :err
echo.
echo 打包完成！程序位于：dist_onefile_lite\CainiaoMonitorLite_SingleFile.exe
pause
exit /b 0
:err
echo.
echo 打包失败，请检查上方错误信息。
pause
exit /b 1
