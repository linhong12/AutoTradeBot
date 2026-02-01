@echo off
cd /d "%~dp0"
echo =============================================
echo        启动 Kronos 交易机器人
echo =============================================
echo.
echo 正在启动交易机器人...
echo 注意：首次启动时可能需要下载字体文件
echo.
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 应用程序退出，错误代码: %ERRORLEVEL%
    echo 请检查以下可能的问题：
    echo 1. Python环境和依赖是否安装完整
    echo 2. 是否有其他程序占用了端口
    echo 3. 防火墙是否阻止了程序运行
)
echo.
pause