@echo off
REM 将当前代码页更改为UTF-8 (65001)，以支持可能出现的中文路径
chcp 65001 >nul

REM --- 自动设置环境变量并启动程序 ---

REM 获取此批处理文件所在的目录 (即我们的项目根目录)
set "CURRENT_DIR=%~dp0"

REM 定义Python可执行文件的绝对路径
set "PYTHON_EXE=%CURRENT_DIR%python_portable\python.exe"

echo ======================================================
echo  Video Editing Toolkit 启动器 v1.1.1
echo ======================================================
echo.
echo  - 正在配置临时Python环境...
echo  - 启动主程序: main.py
echo.
echo  (如果程序因缺少模块而闪退，请先根据README.md手动安装依赖)
echo.

REM 使用我们配置好的环境来执行主Python脚本
"%PYTHON_EXE%" main.py

echo.
echo ======================================================
echo  程序已退出。按任意键关闭此窗口...
echo ======================================================
pause