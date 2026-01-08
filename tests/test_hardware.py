"""
Testy pro Yahboom hardware driver
"""

import pytest
from robot.yahboom_driver import YahboomRiderDriver


def test_yahboom_driver_mock_init():
    """Test inicializace v mock režimu"""
    driver = YahboomRiderDriver(mock_mode=True)
    
    assert driver.mock_mode is True
    assert driver.MAX_SPEED == 255


def test_yahboom_set_motor_speeds():
    """Test nastavení rychlosti motorů"""
    driver = YahboomRiderDriver(mock_mode=True)
    
    driver.set_motor_speeds(100, -50)
    
    assert driver._last_left_speed == 100
    assert driver._last_right_speed == -50


def test_yahboom_set_velocity():
    """Test nastavení velocity"""
    driver = YahboomRiderDriver(mock_mode=True)
    
    driver.set_velocity(linear=0.5, angular=0.0)
    
    # Oba motory by měly být stejné (žádná rotace)
    assert abs(driver._last_left_speed - driver._last_right_speed) < 10


def test_yahboom_stop():
    """Test zastavení"""
    driver = YahboomRiderDriver(mock_mode=True)
    
    driver.set_motor_speeds(100, 100)
    driver.stop()
    
    assert driver._last_left_speed == 0
    assert driver._last_right_speed == 0


def test_yahboom_read_imu():
    """Test čtení IMU"""
    driver = YahboomRiderDriver(mock_mode=True)
    
    imu = driver.read_imu()
    
    assert 'accel_x' in imu
    assert 'accel_y' in imu
    assert 'accel_z' in imu
    assert 'gyro_x' in imu
    assert 'gyro_y' in imu
    assert 'gyro_z' in imu


def test_yahboom_read_ultrasonic():
    """Test čtení ultrazvuku"""
    driver = YahboomRiderDriver(mock_mode=True)
    
    ultrasonic = driver.read_ultrasonic_sensors()
    
    assert 'front' in ultrasonic
    assert 'back' in ultrasonic
    assert 'left' in ultrasonic
    assert 'right' in ultrasonic
    
    # Mock hodnoty by měly být rozumné
    assert 0 < ultrasonic['front'] < 200


def test_yahboom_read_battery():
    """Test čtení baterie"""
    driver = YahboomRiderDriver(mock_mode=True)
    
    battery = driver.read_battery()
    
    assert 'voltage' in battery
    assert 'current' in battery
    assert 'percentage' in battery
    
    assert 0 <= battery['percentage'] <= 100


def test_yahboom_get_telemetry():
    """Test kompletní telemetrie"""
    driver = YahboomRiderDriver(mock_mode=True)
    
    telemetry = driver.get_telemetry()
    
    # Zkontroluj všechny klíče
    required_keys = [
        'motor_left', 'motor_right',
        'encoder_left', 'encoder_right',
        'accel_x', 'accel_y', 'accel_z',
        'gyro_x', 'gyro_y', 'gyro_z',
        'ultrasonic_front', 'ultrasonic_back', 'ultrasonic_left', 'ultrasonic_right',
        'battery_voltage', 'battery_current', 'battery_percentage',
        'timestamp'
    ]
    
    for key in required_keys:
        assert key in telemetry


def test_yahboom_motor_limits():
    """Test limitů motorů"""
    driver = YahboomRiderDriver(mock_mode=True)
    
    # Test přesahu
    driver.set_motor_speeds(300, -300)
    
    # Mělo by být clampnuto
    assert driver._last_left_speed == 255
    assert driver._last_right_speed == -255
