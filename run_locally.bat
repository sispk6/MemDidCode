@echo off
setlocal
title Did-I Personal Assistant

echo ===================================================
echo   Did-I Personal Memory Assistant - Local Launcher
echo ===================================================
echo.

REM 1. Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from python.org
    pause
    exit /b 1
)

REM 2. Check/Create Virtual Environment
if not exist "memoenv" (
    echo [INFO] Creating virtual environment 'memoenv'...
    python -m venv memoenv
)

REM 3. Activate Virtual Environment
call memoenv\Scripts\activate

REM 4. Install Dependencies
echo [INFO] Checking dependencies...
pip install -r requirements.txt >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Dependency check failed. Trying to install with output...
    pip install -r requirements.txt
)

REM 5. Run Application
echo [INFO] Starting application...
python start_standalone.py

pause
