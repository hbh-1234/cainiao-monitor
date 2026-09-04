@echo off
rem ============================================================
rem  打包精简版【目录版】—— 无内嵌浏览器，体积更小，运行零解压
rem  产物：dist_lite\CainiaoMonitorLite\CainiaoMonitorLite.exe
rem ============================================================
cd /d %~dp0

echo [1/3] 安装依赖（首次较慢）...
python -m pip install -r requirements-dev.txt || goto :err

echo [2/3] 生成应用图标...
python tools\gen_icon.py || goto :err

echo [3/3] PyInstaller 打包中...
python -m PyInstaller --clean --noconfirm --distpath dist_lite --workpath build_lite cainiao_monitor_lite_onedir.spec || goto :err

echo.
echo 打包完成！程序位于：dist_lite\CainiaoMonitorLite\CainiaoMonitorLite.exe
pause
exit /b 0

:err
echo.
echo 打包失败，请检查上方错误信息。
pause
exit /b 1
