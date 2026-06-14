@echo off
chcp 65001 >nul
title SubBatch Qwen3 转录引擎安装

echo ============================================
echo   SubBatch Qwen3 高精度转录引擎 - 安装程序
echo ============================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.12+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Python 版本:
python --version
echo.

:: 检查 CUDA
python -c "import torch; print('[2/4] CUDA 可用:', torch.cuda.is_available()); print('    GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')" 2>nul
if %errorlevel% neq 0 (
    echo [2/4] PyTorch 未安装，将自动安装
)

:: 检查 ffmpeg
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] ffmpeg 未安装，音视频处理可能受限
    echo 下载地址: https://ffmpeg.org/download.html
)

:: 创建虚拟环境
echo.
echo [3/4] 创建虚拟环境...
cd /d "%~dp0"
if not exist ".venv" (
    python -m venv .venv
    echo   虚拟环境已创建
) else (
    echo   虚拟环境已存在
)

:: 激活并安装依赖
echo.
echo [4/4] 安装 Python 依赖...
call .venv\Scripts\activate.bat

:: 安装 PyTorch CUDA 版
python -c "import torch" 2>nul
if %errorlevel% neq 0 (
    echo   安装 PyTorch CUDA 版...
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
)

:: 安装项目依赖
pip install -r requirements_qwen3.txt

echo.
echo ============================================
echo   安装完成!
echo.
echo   首次运行时会自动下载 Qwen3 模型(约1.5GB)
echo   模型缓存目录: %~dp0models\qwen3
echo ============================================
echo.

:: 注册 Native Messaging Host
echo [可选] 注册 Chrome Native Messaging Host...
python register_native_host.py

pause
