@echo off
REM 将当前代码页更改为UTF-8 (65001)，以支持可能出现的中文路径
chcp 65001 >nul

REM --- 自动设置环境变量并启动程序 ---

REM 获取此批处理文件所在的目录 (即我们的项目根目录)
set "CURRENT_DIR=%~dp0"

REM 设置我们自己的Python环境的路径
set "PYTHON_DIR=%CURRENT_DIR%python_portable"

REM 关键：将我们的Python和它的Scripts目录临时添加到系统PATH的最前面
REM 这样，当程序调用"python"时，会优先使用我们指定的这个版本
set "PATH=%PYTHON_DIR%;%PYTHON_DIR%\Scripts;%PATH%"

echo ======================================================
echo  FFmpeg Suite 启动器 v1.1
echo ======================================================
echo.
echo  - 正在配置临时Python环境...
echo  - 启动主程序: main.py
echo.

REM 使用我们配置好的环境来执行主Python脚本
python.exe main.py

echo.
echo ======================================================
echo  程序已退出。按任意键关闭此窗口...
echo ======================================================
REM 关键：暂停脚本，以便在Python程序出错时，我们能看到错误信息。
pause