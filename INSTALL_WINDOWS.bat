@echo off
REM Person Tracker - Windows Installation Script
REM Tento skript automaticky nainstaluje všechny závislosti

echo.
echo ========================================
echo   Person Tracker - Installation
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH!
    echo.
    echo Please install Python 3.11 or 3.12 from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation!
    echo.
    pause
    exit /b 1
)

echo Found Python:
python --version
echo.

REM Check if venv already exists
if exist "venv\" (
    echo Virtual environment already exists.
    set /p "RECREATE=Do you want to recreate it? (y/N): "
    if /i "%RECREATE%"=="y" (
        echo Deleting old venv...
        rmdir /s /q venv
    ) else (
        echo Keeping existing venv.
        goto :skip_venv
    )
)

REM Create venv
echo Creating virtual environment...
python -m venv venv
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create virtual environment!
    pause
    exit /b 1
)
echo ✓ Virtual environment created
echo.

:skip_venv

REM Activate venv
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip --quiet
echo ✓ pip upgraded
echo.

REM Install dependencies
echo Installing dependencies...
echo This may take 5-15 minutes depending on your internet speed.
echo.
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to install dependencies!
    echo.
    echo Try manual installation:
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)
echo ✓ Dependencies installed
echo.

REM Install dev dependencies (optional)
set /p "INSTALL_DEV=Install development tools (pytest, linters)? (Y/n): "
if /i not "%INSTALL_DEV%"=="n" (
    echo Installing development dependencies...
    pip install -r requirements-dev.txt --quiet
    echo ✓ Dev dependencies installed
    echo.
)

REM Download models
echo Downloading YOLO model...
python scripts\download_models.py
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Model download failed. It will be downloaded on first run.
    echo.
)

REM Run smoke test
echo.
echo Running smoke test to verify installation...
echo.
set PYTHONPATH=%CD%
python scripts\smoke_test.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: Smoke test failed!
    echo Installation may be incomplete.
    echo.
) else (
    echo.
    echo ========================================
    echo   ✓ Installation completed successfully!
    echo ========================================
    echo.
    echo To start the application, run:
    echo   START_WINDOWS.bat
    echo.
    echo Or manually:
    echo   venv\Scripts\activate
    echo   python main.py
    echo.
)

pause
