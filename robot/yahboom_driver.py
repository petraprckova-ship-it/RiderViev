"""
Yahboom Rider Pi CM4 Hardware Driver

Tento modul poskytuje rozhraní pro ovládání Yahboom Rider robota.
"""

import time
from typing import Tuple, Optional
from loguru import logger
import numpy as np

try:
    # Import Yahboom knihovny (nainstalovaná na Raspberry Pi)
    import smbus
    HAS_I2C = True
except ImportError:
    logger.warning("smbus není k dispozici - používám mock režim")
    HAS_I2C = False


class YahboomRiderDriver:
    """
    Driver pro Yahboom Rider Pi CM4 robot
    
    Hardware features:
    - Dual DC motors s enkodéry
    - MPU6050 6-axis IMU (akcelerometr + gyroskop)
    - 4x HC-SR04 ultrazvukové senzory (přední, zadní, levý, pravý)
    - RGB LED matrix
    - IR senzory
    - Servo ovládání (pro kameru pan/tilt)
    """
    
    # I2C adresy
    I2C_ADDRESS = 0x16
    MPU6050_ADDRESS = 0x68
    
    # Registry
    REG_MOTOR_LEFT = 0x01
    REG_MOTOR_RIGHT = 0x02
    REG_SERVO_1 = 0x03
    REG_SERVO_2 = 0x04
    REG_LED = 0x05
    REG_ULTRASONIC = 0x10
    REG_IR = 0x20
    
    # Motor parametry
    MAX_SPEED = 255
    WHEEL_DIAMETER = 0.066  # 66mm
    WHEEL_BASE = 0.158  # 158mm
    ENCODER_RESOLUTION = 390  # pulses per revolution
    
    def __init__(self, i2c_bus: int = 1, mock_mode: bool = False):
        """
        Args:
            i2c_bus: I2C bus číslo (obvykle 1 na Raspberry Pi)
            mock_mode: True pro mock režim bez hardware
        """
        self.mock_mode = mock_mode or not HAS_I2C
        
        if not self.mock_mode:
            try:
                self.bus = smbus.SMBus(i2c_bus)
                logger.info(f"I2C bus {i2c_bus} inicializován")
                
                # Inicializace hardware
                self._init_hardware()
                
            except Exception as e:
                logger.error(f"Nelze inicializovat I2C: {e}")
                self.mock_mode = True
                
        if self.mock_mode:
            logger.warning("Yahboom driver běží v MOCK režimu")
            
        # Interní stavy
        self._last_left_speed = 0
        self._last_right_speed = 0
        self._last_encoder_left = 0
        self._last_encoder_right = 0
        
    def _init_hardware(self):
        """Inicializace hardware"""
        # Reset motorů
        self.set_motor_speeds(0, 0)
        
        # Reset LED
        self.set_rgb_led(0, 0, 0)
        
        # Inicializace MPU6050
        try:
            # Wake up MPU6050
            self.bus.write_byte_data(self.MPU6050_ADDRESS, 0x6B, 0)
            time.sleep(0.1)
            
            # Nastav full scale range
            self.bus.write_byte_data(self.MPU6050_ADDRESS, 0x1B, 0x00)  # ±250°/s
            self.bus.write_byte_data(self.MPU6050_ADDRESS, 0x1C, 0x00)  # ±2g
            
            logger.info("MPU6050 inicializován")
            
        except Exception as e:
            logger.warning(f"Nelze inicializovat MPU6050: {e}")
            
    def set_motor_speeds(self, left: int, right: int):
        """
        Nastav rychlosti motorů
        
        Args:
            left: Levý motor (-255 až 255)
            right: Pravý motor (-255 až 255)
        """
        # Clamp values
        left = max(-self.MAX_SPEED, min(self.MAX_SPEED, left))
        right = max(-self.MAX_SPEED, min(self.MAX_SPEED, right))
        
        if not self.mock_mode:
            try:
                # Převod na unsigned + směr
                left_dir = 1 if left >= 0 else 0
                right_dir = 1 if right >= 0 else 0
                
                left_speed = abs(left)
                right_speed = abs(right)
                
                # Zápis přes I2C
                self.bus.write_i2c_block_data(
                    self.I2C_ADDRESS,
                    self.REG_MOTOR_LEFT,
                    [left_dir, left_speed]
                )
                
                self.bus.write_i2c_block_data(
                    self.I2C_ADDRESS,
                    self.REG_MOTOR_RIGHT,
                    [right_dir, right_speed]
                )
                
            except Exception as e:
                logger.error(f"Chyba při nastavení motorů: {e}")
                
        self._last_left_speed = left
        self._last_right_speed = right
        
    def set_velocity(self, linear: float, angular: float):
        """
        Nastav rychlost (linear/angular) a převeď na kola
        
        Args:
            linear: Lineární rychlost (m/s, -1.0 až 1.0)
            angular: Angulární rychlost (rad/s, -2.0 až 2.0)
        """
        # Diferenciální pohon
        # v_left = linear - (angular * wheel_base / 2)
        # v_right = linear + (angular * wheel_base / 2)
        
        v_left = linear - (angular * self.WHEEL_BASE / 2.0)
        v_right = linear + (angular * self.WHEEL_BASE / 2.0)
        
        # Převod m/s na motor PWM (0-255)
        # Předpokládáme max rychlost 1.0 m/s = 255 PWM
        left_pwm = int(v_left * self.MAX_SPEED)
        right_pwm = int(v_right * self.MAX_SPEED)
        
        self.set_motor_speeds(left_pwm, right_pwm)
        
    def stop(self):
        """Zastav všechny motory"""
        self.set_motor_speeds(0, 0)
        
    def read_encoders(self) -> Tuple[int, int]:
        """
        Čtení enkodérů
        
        Returns:
            (left_pulses, right_pulses)
        """
        if self.mock_mode:
            # Simulace - inkrementuj podle rychlosti
            self._last_encoder_left += abs(self._last_left_speed) // 10
            self._last_encoder_right += abs(self._last_right_speed) // 10
            return (self._last_encoder_left, self._last_encoder_right)
            
        try:
            # Čtení přes I2C
            data = self.bus.read_i2c_block_data(self.I2C_ADDRESS, 0x30, 8)
            
            # Parsování (4 bajty pro každý enkodér)
            left = int.from_bytes(data[0:4], byteorder='big', signed=True)
            right = int.from_bytes(data[4:8], byteorder='big', signed=True)
            
            return (left, right)
            
        except Exception as e:
            logger.error(f"Chyba při čtení enkodérů: {e}")
            return (0, 0)
            
    def read_imu(self) -> dict:
        """
        Čtení MPU6050 IMU
        
        Returns:
            Dict s klíči: accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z
        """
        if self.mock_mode:
            return {
                'accel_x': 0.0,
                'accel_y': 0.0,
                'accel_z': 9.81,
                'gyro_x': 0.0,
                'gyro_y': 0.0,
                'gyro_z': 0.0
            }
            
        try:
            # Čtení 14 bajtů (accel + temp + gyro)
            data = self.bus.read_i2c_block_data(self.MPU6050_ADDRESS, 0x3B, 14)
            
            # Parsování
            accel_x = int.from_bytes(data[0:2], byteorder='big', signed=True) / 16384.0 * 9.81
            accel_y = int.from_bytes(data[2:4], byteorder='big', signed=True) / 16384.0 * 9.81
            accel_z = int.from_bytes(data[4:6], byteorder='big', signed=True) / 16384.0 * 9.81
            
            gyro_x = int.from_bytes(data[8:10], byteorder='big', signed=True) / 131.0 * (np.pi / 180.0)
            gyro_y = int.from_bytes(data[10:12], byteorder='big', signed=True) / 131.0 * (np.pi / 180.0)
            gyro_z = int.from_bytes(data[12:14], byteorder='big', signed=True) / 131.0 * (np.pi / 180.0)
            
            return {
                'accel_x': accel_x,
                'accel_y': accel_y,
                'accel_z': accel_z,
                'gyro_x': gyro_x,
                'gyro_y': gyro_y,
                'gyro_z': gyro_z
            }
            
        except Exception as e:
            logger.error(f"Chyba při čtení IMU: {e}")
            return {
                'accel_x': 0.0,
                'accel_y': 0.0,
                'accel_z': 0.0,
                'gyro_x': 0.0,
                'gyro_y': 0.0,
                'gyro_z': 0.0
            }
            
    def read_ultrasonic_sensors(self) -> dict:
        """
        Čtení ultrazvukových senzorů
        
        Returns:
            Dict s klíči: front, back, left, right (vzdálenosti v cm)
        """
        if self.mock_mode:
            # Simulace - náhodné hodnoty
            import random
            return {
                'front': random.uniform(20, 150),
                'back': random.uniform(20, 150),
                'left': random.uniform(20, 150),
                'right': random.uniform(20, 150)
            }
            
        try:
            # Čtení přes I2C
            data = self.bus.read_i2c_block_data(self.I2C_ADDRESS, self.REG_ULTRASONIC, 8)
            
            front = int.from_bytes(data[0:2], byteorder='big')
            back = int.from_bytes(data[2:4], byteorder='big')
            left = int.from_bytes(data[4:6], byteorder='big')
            right = int.from_bytes(data[6:8], byteorder='big')
            
            return {
                'front': front,
                'back': back,
                'left': left,
                'right': right
            }
            
        except Exception as e:
            logger.error(f"Chyba při čtení ultrazvukových senzorů: {e}")
            return {
                'front': 0,
                'back': 0,
                'left': 0,
                'right': 0
            }
            
    def read_battery(self) -> dict:
        """
        Čtení stavu baterie
        
        Returns:
            Dict s klíči: voltage, current, percentage
        """
        if self.mock_mode:
            return {
                'voltage': 12.0,
                'current': 0.5,
                'percentage': 85.0
            }
            
        try:
            # Čtení přes I2C
            data = self.bus.read_i2c_block_data(self.I2C_ADDRESS, 0x40, 6)
            
            voltage = int.from_bytes(data[0:2], byteorder='big') / 100.0
            current = int.from_bytes(data[2:4], byteorder='big') / 1000.0
            percentage = int.from_bytes(data[4:6], byteorder='big') / 10.0
            
            return {
                'voltage': voltage,
                'current': current,
                'percentage': percentage
            }
            
        except Exception as e:
            logger.error(f"Chyba při čtení baterie: {e}")
            return {
                'voltage': 0.0,
                'current': 0.0,
                'percentage': 0.0
            }
            
    def set_rgb_led(self, r: int, g: int, b: int):
        """
        Nastav RGB LED
        
        Args:
            r, g, b: 0-255
        """
        if self.mock_mode:
            return
            
        try:
            self.bus.write_i2c_block_data(
                self.I2C_ADDRESS,
                self.REG_LED,
                [r, g, b]
            )
        except Exception as e:
            logger.error(f"Chyba při nastavení LED: {e}")
            
    def set_servo_angles(self, pan: int, tilt: int):
        """
        Nastav servo úhly (pro kameru)
        
        Args:
            pan: Horizontální úhel (0-180)
            tilt: Vertikální úhel (0-180)
        """
        pan = max(0, min(180, pan))
        tilt = max(0, min(180, tilt))
        
        if self.mock_mode:
            return
            
        try:
            self.bus.write_byte_data(self.I2C_ADDRESS, self.REG_SERVO_1, pan)
            self.bus.write_byte_data(self.I2C_ADDRESS, self.REG_SERVO_2, tilt)
        except Exception as e:
            logger.error(f"Chyba při nastavení serv: {e}")
            
    def get_telemetry(self) -> dict:
        """
        Získej kompletní telemetrii
        
        Returns:
            Dict se všemi daty
        """
        imu = self.read_imu()
        ultrasonic = self.read_ultrasonic_sensors()
        battery = self.read_battery()
        encoders = self.read_encoders()
        
        return {
            # Motors
            'motor_left': self._last_left_speed,
            'motor_right': self._last_right_speed,
            
            # Encoders
            'encoder_left': encoders[0],
            'encoder_right': encoders[1],
            
            # IMU
            'accel_x': imu['accel_x'],
            'accel_y': imu['accel_y'],
            'accel_z': imu['accel_z'],
            'gyro_x': imu['gyro_x'],
            'gyro_y': imu['gyro_y'],
            'gyro_z': imu['gyro_z'],
            
            # Ultrasonic
            'ultrasonic_front': ultrasonic['front'],
            'ultrasonic_back': ultrasonic['back'],
            'ultrasonic_left': ultrasonic['left'],
            'ultrasonic_right': ultrasonic['right'],
            
            # Battery
            'battery_voltage': battery['voltage'],
            'battery_current': battery['current'],
            'battery_percentage': battery['percentage'],
            
            # System
            'timestamp': time.time()
        }
