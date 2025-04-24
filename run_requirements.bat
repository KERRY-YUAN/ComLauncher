@echo off

set "python_exec=python.exe"
set "requirements_txt=%~dp0\requirements.txt"
set "venv_folder=%~dp0\venv"

rem 检测是否存在venv文件夹
if not exist "%venv_folder%" (
    echo Creating virtual environment...
    %python_exec% -m venv "%venv_folder%"
    echo Virtual environment created successfully.
) else (
    echo Virtual environment already exists.
)

echo Installing with ComfyUI Portable
echo .
echo Install requirement.txt...
for /f "delims=" %%i in (%requirements_txt%) do (
    %python_exec% -s -m pip install "%%i"
)

echo .
echo Install Finish!
pause

rem Then, install the correct PyTorch version / 然后，安装正确的 PyTorch 版本
rem (Example for CUDA 11.8, replace with user's correct command)
rem (CUDA 11.8 示例，替换为用户正确的命令)
rem pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
rem (CUDA 12.4示例，替换为用户正确的命令)
rem pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
rem (CUDA 12.6示例，替换为用户正确的命令)
rem pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126    