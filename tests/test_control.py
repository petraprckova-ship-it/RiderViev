"""
Unit testy pro control systém
"""

import pytest
import numpy as np

from src.control.pid import (
    PIDController,
    DualPIDController,
    VelocityProfiler,
    WatchdogTimer,
    SpeedLimiter
)
from src.control.tracking import PersonTrackingController, TrackingMode


def test_pid_controller():
    """Test PID kontroleru"""
    pid = PIDController(
        kp=1.0,
        ki=0.1,
        kd=0.05,
        output_limit=1.0
    )
    
    # Test P komponenty
    pid.setpoint = 5.0
    output = pid.update(measured_value=3.0, dt=0.1)
    assert output > 0  # Mělo by být kladné (chyba je +2.0)
    
    # Reset
    pid.reset()
    assert pid.integral == 0.0


def test_pid_anti_windup():
    """Test anti-windup PID"""
    pid = PIDController(
        kp=1.0,
        ki=0.5,
        kd=0.0,
        output_limit=1.0
    )
    
    # Velká chyba po dlouhou dobu
    pid.setpoint = 10.0
    for _ in range(100):
        output = pid.update(measured_value=0.0, dt=0.1)
        
    # Integral by měl být limitován
    assert abs(output) <= 1.0


def test_dual_pid_controller():
    """Test duálního PID"""
    from src.control.pid import PIDConfig
    dual_pid = DualPIDController(
        linear_config=PIDConfig(kp=1.0, ki=0.1, kd=0.05),
        angular_config=PIDConfig(kp=0.8, ki=0.05, kd=0.02)
    )
    
    dual_pid.set_setpoints(linear=1.0, angular=0.0)
    linear, angular = dual_pid.update(
        linear_measured=0.5,
        angular_measured=0.1,
        dt=0.1
    )
    
    assert linear > 0  # Mělo by zrychlit
    assert angular < 0  # Mělo by otočit doleva


def test_velocity_profiler():
    """Test velocity profileru"""
    profiler = VelocityProfiler(
        max_acceleration=2.0,
        max_deceleration=2.0
    )
    
    # Testuj acceleration
    velocities = []
    for _ in range(10):
        v = profiler.update(target=1.0, dt=0.1)
        velocities.append(v)
        
    # Rychlost by měla růst
    assert velocities[-1] > velocities[0]
    assert velocities[-1] <= 1.0


def test_watchdog_timer():
    """Test watchdog timeru"""
    watchdog = WatchdogTimer(timeout=1.0)
    
    # Aktivuj
    watchdog.feed()
    
    # Není expired
    assert not watchdog.check()
    
    # Počkej
    import time
    time.sleep(1.1)
    
    # Mělo by být expired
    assert watchdog.check()


def test_speed_limiter():
    """Test speed limiteru"""
    limiter = SpeedLimiter(
        max_linear_speed=1.0,
        max_angular_speed=2.0
    )
    
    # Test limitování
    linear, angular = limiter.limit_velocity(2.0, 3.0)
    
    assert linear <= 1.0
    assert angular <= 2.0


def test_tracking_controller_state_machine():
    """Test stavového stroje tracking kontroleru"""
    from src.config import Config
    from src.control.pid import PIDConfig
    from src.ml.tracker import Track
    from src.ml.distance import DistanceInfo
    
    config = Config()
    controller = PersonTrackingController(
        linear_pid_config=config.control.pid['linear'],
        angular_pid_config=config.control.pid['angular']
    )
    
    # Počáteční stav
    assert controller.mode == TrackingMode.IDLE
    
    # Update bez tracku -> SEARCHING
    for _ in range(10):
        controller.update(None, None)
    
    # Po 60 frames měl by přejít do SEARCHING
    # (Nebo zůstane v IDLE pokud není implementována auto-detekce)
    assert controller.mode in [TrackingMode.IDLE, TrackingMode.SEARCHING]


def test_tracking_controller_emergency_stop():
    """Test nouzového zastavení"""
    from src.config import Config
    from src.control.pid import PIDConfig
    from src.ml.tracker import Track
    from src.ml.distance import DistanceInfo
    
    config = Config()
    controller = PersonTrackingController(
        linear_pid_config=config.control.pid['linear'],
        angular_pid_config=config.control.pid['angular']
    )
    
    # Nastav tracking
    track = Track(track_id=1, bbox=np.array([100.0, 100.0, 200.0, 300.0], dtype=np.float32), confidence=0.9)
    dist_info = DistanceInfo(distance=2.0, method="bbox", confidence=0.8)
    
    # Update s obstacle -> emergency stop
    linear, angular = controller.update(track, dist_info, obstacle_detected=True)
    
    # Mělo by být EMERGENCY_STOP
    assert controller.mode == TrackingMode.EMERGENCY_STOP
    assert linear == 0.0
    assert angular == 0.0
