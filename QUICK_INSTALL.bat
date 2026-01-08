@echo off
REM Person Tracker - Quick Install & Run (All-in-One)
REM Tento skript stahne projekt a nainstaluje vse automaticky

echo ========================================
echo   Person Tracker - Quick Install
echo ========================================
echo.

REM Check if we're in project folder
if not exist "main.py" (
    echo Projekt nebyl nalezen. Stahuji z GitHubu...
    echo.
    
    REM Check git
    git --version >nul 2>&1 || (echo ERROR: Git not installed! Install from git-scm.com & pause & exit /b 1)
    
    REM Clone repository
    echo [1/7] Cloning repository...
    git clone https://github.com/petraprckova-ship-it/RiderViev.git
    if %ERRORLEVEL% NEQ 0 (echo ERROR: Git clone failed! & pause & exit /b 1)
    
    echo Vstupuji do slozky projektu...
    cd RiderViev
    echo.
) else (
    echo [1/7] Project folder detected - skipping download
)

REM Check Python
python --version >nul 2>&1 || (echo ERROR: Python not installed! Install from python.org & pause & exit /b 1)
echo [2/7] Python found: & python --version

REM Create venv
if not exist venv (echo [3/7] Creating virtual environment... & python -m venv venv) else (echo [3/7] Virtual environment exists)

REM Activate and install
echo [4/7] Installing dependencies (this may take 5-15 minutes)...
call venv\Scripts\activate.bat && python -m pip install --upgrade pip -q && pip install -r requirements.txt -q || (echo ERROR: Installation failed! & pause & exit /b 1)

REM Download model
echo [5/7] Downloading YOLO model...
python scripts\download_models.py 2>nul || echo Model will download on first run

REM Verify
echo [6/7] Running verification...
set PYTHONPATH=%CD%
python scripts\smoke_test.py || (echo WARNING: Verification failed & pause)

REM Start
echo [7/7] Starting application...
echo.
echo ========================================
echo   ^>^> Application starting...
echo ========================================
echo.
python main.py
