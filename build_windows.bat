@echo off
REM Build script for PingMonitor on Windows
REM This script builds the Windows .exe executable

echo Building PingMonitor for Windows...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    echo Please install Python 3.8+ and add it to PATH
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "packaging_env" (
    echo Creating virtual environment...
    python -m venv packaging_env
)

REM Activate virtual environment
echo Activating virtual environment...
call packaging_env\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install pyinstaller Pillow

REM Run the build script
echo Running build...
python build.py

echo.
echo Build complete! Check the dist/ directory for PingMonitor.exe
pause