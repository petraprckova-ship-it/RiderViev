# Person Tracker - Quick Install & Run (PowerShell)
# Tento skript stahne projekt a nainstaluje vse automaticky
# Spustte: powershell -ExecutionPolicy Bypass -File QUICK_INSTALL.ps1

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Person Tracker - Quick Install" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if we're in project folder
if (-not (Test-Path "main.py")) {
    Write-Host "Projekt nebyl nalezen. Stahuji z GitHubu..." -ForegroundColor Yellow
    Write-Host ""
    
    # Check git
    try {
        $gitVersion = git --version 2>&1
        Write-Host "✓ Git found: $gitVersion" -ForegroundColor Green
    } catch {
        Write-Host "✗ ERROR: Git not installed!" -ForegroundColor Red
        Write-Host "Install from: https://git-scm.com/downloads" -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }
    
    # Clone repository
    Write-Host "`n[1/7] Cloning repository..." -ForegroundColor Yellow
    git clone https://github.com/petraprckova-ship-it/RiderViev.git
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Git clone failed!" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    
    Write-Host "✓ Repository cloned" -ForegroundColor Green
    Write-Host "Vstupuji do slozky projektu..." -ForegroundColor Gray
    Set-Location RiderViev
    Write-Host ""
} else {
    Write-Host "[1/7] Project folder detected - skipping download" -ForegroundColor Green
}

# Check Python
Write-Host "`n[2/7] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ ERROR: Python not installed!" -ForegroundColor Red
    Write-Host "Install from: https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Create venv
Write-Host "`n[3/7] Setting up virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    python -m venv venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "✓ Virtual environment exists" -ForegroundColor Green
}

# Activate and upgrade pip
Write-Host "`n[4/7] Installing dependencies..." -ForegroundColor Yellow
Write-Host "This may take 5-15 minutes..." -ForegroundColor Gray
& venv\Scripts\Activate.ps1
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "✗ Installation failed!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Download model
Write-Host "`n[5/7] Downloading YOLO model..." -ForegroundColor Yellow
python scripts\download_models.py 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Model downloaded" -ForegroundColor Green
} else {
    Write-Host "⚠ Model will download on first run" -ForegroundColor Yellow
}

# Verify installation
Write-Host "`n[6/7] Verifying installation..." -ForegroundColor Yellow
$env:PYTHONPATH = $PWD
python scripts\smoke_test.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Verification passed" -ForegroundColor Green
} else {
    Write-Host "⚠ Verification failed - check errors above" -ForegroundColor Yellow
}

# Start application
Write-Host "`n[7/7] Starting application..." -ForegroundColor Yellow
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  >> Application starting..." -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Gray

python main.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n✗ Application exited with error" -ForegroundColor Red
    Read-Host "Press Enter to exit"
}
