@echo off
REM Person Tracker - Windows Startup Script
REM Tento skript automaticky aktivuje venv a spustí aplikaci

echo.
echo ========================================
echo   Person Tracker - Starting...
echo ========================================
echo.

REM Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run INSTALL_WINDOWS.bat first
    echo.
    pause
    exit /b 1
)

REM Activate venv
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found in venv!
    echo Please reinstall dependencies
    pause
    exit /b 1
)

echo Starting Person Tracker...
echo.
echo Press Ctrl+C to stop
echo.

REM Run the application
python main.py

REM If app crashes, pause to see error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================
    echo   Application exited with error
    echo ========================================
    echo.
    pause
)
