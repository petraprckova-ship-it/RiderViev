#!/usr/bin/env python3
"""
Rychlý smoke test - zkontroluje základní funkčnost
"""

import sys
from pathlib import Path

print("🧪 Person Tracker - Smoke Test")
print("=" * 50)

# Test 1: Import základních modulů
print("\n1️⃣  Testování importů...")
try:
    # Disable GUI imports in headless environment
    import os
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    
    from src.config import Config, init_config
    from src.ml.detector import PersonDetector, Detection
    from src.ml.tracker import ByteTracker, Track
    from src.ml.distance import BBoxDistanceEstimator
    from src.control.pid import PIDController, DualPIDController
    from src.control.tracking import PersonTrackingController, TrackingMode
    from src.network.client import RobotClient
    # Skip video/UI imports in headless
    # from src.video.gstreamer_client import GStreamerClient
    from robot.yahboom_driver import YahboomRiderDriver
    
    print("   ✅ Všechny moduly importovány úspěšně")
except ImportError as e:
    print(f"   ❌ Chyba při importu: {e}")
    sys.exit(1)

# Test 2: Konfigurace
print("\n2️⃣  Testování konfigurace...")
try:
    config = Config()
    assert config.app.name == "Person Tracker"
    assert config.app.language == "cs"
    print("   ✅ Konfigurace OK")
except Exception as e:
    print(f"   ❌ Chyba v konfiguraci: {e}")
    sys.exit(1)

# Test 3: ML komponenty
print("\n3️⃣  Testování ML komponent...")
try:
    import numpy as np
    
    # Detection
    det = Detection(
        bbox=[100, 100, 200, 300],
        confidence=0.9,
        class_id=0,
        class_name="person"
    )
    assert det.width == 100
    assert det.height == 200
    
    # Tracker
    tracker = ByteTracker()
    assert len(tracker.tracks) == 0
    
    # Distance estimator
    estimator = BBoxDistanceEstimator()
    distance = estimator.estimate([100, 100, 200, 300])
    assert distance.distance > 0
    
    print("   ✅ ML komponenty OK")
except Exception as e:
    print(f"   ❌ Chyba v ML komponentách: {e}")
    sys.exit(1)

# Test 4: Control systém
print("\n4️⃣  Testování control systému...")
try:
    pid = PIDController(kp=1.0, ki=0.1, kd=0.05)
    pid.setpoint = 5.0
    output = pid.update(measured_value=3.0, dt=0.1)
    assert output > 0
    
    from src.control.pid import PIDConfig
    dual_pid = DualPIDController(
        linear_config=PIDConfig(kp=1.0, ki=0.1, kd=0.05),
        angular_config=PIDConfig(kp=0.8, ki=0.05, kd=0.02)
    )
    
    print("   ✅ Control systém OK")
except Exception as e:
    print(f"   ❌ Chyba v control systému: {e}")
    sys.exit(1)

# Test 5: Hardware driver (mock)
print("\n5️⃣  Testování hardware driveru (mock)...")
try:
    driver = YahboomRiderDriver(mock_mode=True)
    driver.set_motor_speeds(100, 100)
    
    imu = driver.read_imu()
    assert 'accel_x' in imu
    
    ultrasonic = driver.read_ultrasonic_sensors()
    assert 'front' in ultrasonic
    
    battery = driver.read_battery()
    assert 'percentage' in battery
    
    telemetry = driver.get_telemetry()
    assert 'timestamp' in telemetry
    
    driver.stop()
    
    print("   ✅ Hardware driver OK")
except Exception as e:
    print(f"   ❌ Chyba v hardware driveru: {e}")
    sys.exit(1)

# Test 6: Struktura souborů
print("\n6️⃣  Kontrola struktury souborů...")
try:
    required_files = [
        "main.py",
        "README.md",
        "LICENSE",
        "requirements.txt",
        "requirements-dev.txt",
        "config/default_config.yaml",
        "docs/installation.md",
        "docs/quick_start.md",
        "docs/architecture.md",
        "scripts/download_models.py",
        "scripts/verify_installation.py",
        "robot/robot_service.py",
        "robot/yahboom_driver.py",
        "robot/install.sh",
        ".github/workflows/ci.yml",
        "Makefile",
        "Dockerfile",
        "pyproject.toml",
    ]
    
    missing = []
    for file in required_files:
        if not Path(file).exists():
            missing.append(file)
    
    if missing:
        print(f"   ⚠️  Chybějící soubory: {', '.join(missing)}")
    else:
        print("   ✅ Všechny klíčové soubory přítomny")
except Exception as e:
    print(f"   ❌ Chyba při kontrole souborů: {e}")

# Test 7: Python verze
print("\n7️⃣  Kontrola Python verze...")
if sys.version_info >= (3, 11):
    print(f"   ✅ Python {sys.version_info.major}.{sys.version_info.minor} OK")
else:
    print(f"   ⚠️  Python {sys.version_info.major}.{sys.version_info.minor} - doporučeno 3.11+")

print("\n" + "=" * 50)
print("✅ Smoke test dokončen - základní funkčnost OK!")
print("\nDalší kroky:")
print("  1. Spusťte testy: make test")
print("  2. Stáhněte modely: python scripts/download_models.py")
print("  3. Spusťte aplikaci: python main.py")
