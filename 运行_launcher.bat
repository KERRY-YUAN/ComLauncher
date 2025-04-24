@echo off

REM --- Get the directory where this batch script is located ---
REM --- 获取此批处理脚本所在的目录 ---
SET "SCRIPT_DIR=%~dp0"

REM --- Construct the full paths ---
REM --- 构建完整路径 ---
SET "PYTHONW_EXE=%SCRIPT_DIR%venv\Scripts\pythonw.exe"
SET "LAUNCHER_PY=%SCRIPT_DIR%launcher.py"

REM --- Check if files exist (optional but good practice) ---
REM --- 检查文件是否存在（可选，但建议） ---
IF NOT EXIST "%PYTHONW_EXE%" (
    ECHO Error: PythonW not found at "%PYTHONW_EXE%"
    PAUSE
    EXIT /B 1
)
IF NOT EXIST "%LAUNCHER_PY%" (
    ECHO Error: Launcher script not found at "%LAUNCHER_PY%"
    PAUSE
    EXIT /B 1
)

REM --- Run the launcher script using pythonw.exe ---
REM --- 使用 pythonw.exe 运行启动器脚本 ---
REM --- The START command helps ensure the batch file can exit immediately. ---
REM --- START 命令有助于确保批处理文件可以立即退出。 ---
REM --- The "" is a placeholder for the window title (required by START). ---
REM --- "" 是窗口标题的占位符（START 命令需要）。 ---
START "" "%PYTHONW_EXE%" "%LAUNCHER_PY%"

REM --- Exit the batch script ---
REM --- 退出批处理脚本 ---
EXIT /B 0