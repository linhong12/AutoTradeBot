@echo off

REM Kronos交易机器人打包脚本
REM 运行此脚本以构建可执行文件

echo === Kronos交易机器人打包工具 ===
echo.echo 正在运行打包脚本...
python build_exe.py

echo.echo 按任意键退出...
pause > nul
