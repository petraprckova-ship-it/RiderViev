"""
PID regulátor pro plynulé řízení robota
"""

import time
from dataclasses import dataclass
from typing import Optional
import numpy as np
from loguru import logger


@dataclass
class PIDConfig:
    """Konfigurace PID regulátoru"""
    kp: float = 1.0
    ki: float = 0.1
    kd: float = 0.05
    output_limit: float = 1.0
    integral_limit: float = 1.0
    deadband: float = 0.0


class PIDController:
    """
    PID regulátor s anti-windup a derivativní filtrací
    """

    def __init__(
        self,
        kp: float = 1.0,
        ki: float = 0.1,
        kd: float = 0.05,
        output_limit: float = 1.0,
        integral_limit: float = 1.0,
        deadband: float = 0.0,
        derivative_filter: float = 0.1
    ):
        """
        Args:
            kp: Proporcionální zisk
            ki: Integrální zisk
            kd: Derivační zisk
            output_limit: Limit výstupu
            integral_limit: Limit integrační složky (anti-windup)
            deadband: Deadband kolem setpointu
            derivative_filter: Filtr pro derivaci (0-1, vyšší = více filtrování)
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_limit = output_limit
        self.integral_limit = integral_limit
        self.deadband = deadband
        self.derivative_filter = derivative_filter

        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_derivative = 0.0
        self.prev_time: Optional[float] = None

        self.setpoint = 0.0

    def update(self, measured_value: float, dt: Optional[float] = None) -> float:
        """
        Aktualizuj PID a vypočítej výstup

        Args:
            measured_value: Naměřená hodnota
            dt: Časový krok (None = automaticky)

        Returns:
            Výstupní signál
        """
        current_time = time.perf_counter()

        # Vypočítej dt
        if dt is None:
            if self.prev_time is not None:
                dt = current_time - self.prev_time
            else:
                dt = 0.02  # Výchozí 50Hz
        self.prev_time = current_time

        # Chyba
        error = self.setpoint - measured_value

        # Deadband
        if abs(error) < self.deadband:
            error = 0.0

        # Proporcionální složka
        p_term = self.kp * error

        # Integrální složka s anti-windup
        self.integral += error * dt
        self.integral = np.clip(
            self.integral,
            -self.integral_limit / self.ki if self.ki != 0 else 0,
            self.integral_limit / self.ki if self.ki != 0 else 0
        )
        i_term = self.ki * self.integral

        # Derivační složka s filtrací
        if dt > 0:
            derivative = (error - self.prev_error) / dt
            # Low-pass filter
            filtered_derivative = (
                self.derivative_filter * self.prev_derivative +
                (1 - self.derivative_filter) * derivative
            )
            d_term = self.kd * filtered_derivative
            self.prev_derivative = filtered_derivative
        else:
            d_term = 0.0

        self.prev_error = error

        # Celkový výstup
        output = p_term + i_term + d_term

        # Saturace výstupu
        output = np.clip(output, -self.output_limit, self.output_limit)

        return output

    def set_setpoint(self, setpoint: float):
        """Nastav cílovou hodnotu"""
        self.setpoint = setpoint

    def reset(self):
        """Reset PID (integral, derivace)"""
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_derivative = 0.0
        self.prev_time = None
        logger.debug("PID resetován")

    def set_gains(self, kp: Optional[float] = None, ki: Optional[float] = None, kd: Optional[float] = None):
        """
        Nastav PID zisky

        Args:
            kp: Proporcionální zisk
            ki: Integrální zisk
            kd: Derivační zisk
        """
        if kp is not None:
            self.kp = kp
        if ki is not None:
            self.ki = ki
        if kd is not None:
            self.kd = kd
        logger.info(f"PID zisky nastaveny: Kp={self.kp}, Ki={self.ki}, Kd={self.kd}")

    def get_error(self) -> float:
        """Získej aktuální chybu"""
        return self.prev_error


class DualPIDController:
    """
    Duální PID pro lineární a angulární rychlost
    """

    def __init__(
        self,
        linear_config: PIDConfig,
        angular_config: PIDConfig
    ):
        """
        Args:
            linear_config: Konfigurace pro lineární PID
            angular_config: Konfigurace pro angulární PID
        """
        self.linear_pid = PIDController(
            kp=linear_config.kp,
            ki=linear_config.ki,
            kd=linear_config.kd,
            output_limit=linear_config.output_limit,
            integral_limit=linear_config.integral_limit,
            deadband=linear_config.deadband
        )

        self.angular_pid = PIDController(
            kp=angular_config.kp,
            ki=angular_config.ki,
            kd=angular_config.kd,
            output_limit=angular_config.output_limit,
            integral_limit=angular_config.integral_limit,
            deadband=angular_config.deadband
        )

    def update(
        self,
        linear_measured: float,
        angular_measured: float,
        dt: Optional[float] = None
    ) -> tuple[float, float]:
        """
        Aktualizuj oba PID

        Args:
            linear_measured: Naměřená lineární rychlost
            angular_measured: Naměřená angulární rychlost
            dt: Časový krok

        Returns:
            (linear_output, angular_output)
        """
        linear_output = self.linear_pid.update(linear_measured, dt)
        angular_output = self.angular_pid.update(angular_measured, dt)

        return linear_output, angular_output

    def set_setpoints(self, linear: float, angular: float):
        """
        Nastav setpointy

        Args:
            linear: Cílová lineární rychlost
            angular: Cílová angulární rychlost
        """
        self.linear_pid.set_setpoint(linear)
        self.angular_pid.set_setpoint(angular)

    def reset(self):
        """Reset obou PID"""
        self.linear_pid.reset()
        self.angular_pid.reset()

    def get_errors(self) -> tuple[float, float]:
        """Získej chyby obou PID"""
        return self.linear_pid.get_error(), self.angular_pid.get_error()


class VelocityProfiler:
    """
    Generátor trapezoidního rychlostního profilu
    """

    def __init__(
        self,
        max_acceleration: float = 0.4,
        max_deceleration: float = 0.5
    ):
        """
        Args:
            max_acceleration: Maximální zrychlení (m/s²)
            max_deceleration: Maximální zpomalení (m/s²)
        """
        self.max_acceleration = max_acceleration
        self.max_deceleration = max_deceleration

        self.current_velocity = 0.0
        self.target_velocity = 0.0

    def update(self, target: float, dt: float) -> float:
        """
        Aktualizuj profil

        Args:
            target: Cílová rychlost
            dt: Časový krok

        Returns:
            Aktuální rychlost po aplikaci zrychlení
        """
        self.target_velocity = target

        velocity_diff = self.target_velocity - self.current_velocity

        # Určení zrychlení
        if velocity_diff > 0:
            # Zrychlujeme
            max_change = self.max_acceleration * dt
            actual_change = min(velocity_diff, max_change)
        else:
            # Zpomalujeme
            max_change = self.max_deceleration * dt
            actual_change = max(velocity_diff, -max_change)

        self.current_velocity += actual_change

        return self.current_velocity

    def reset(self, initial_velocity: float = 0.0):
        """Reset na danou rychlost"""
        self.current_velocity = initial_velocity
        self.target_velocity = initial_velocity

    def get_current_velocity(self) -> float:
        """Získej aktuální rychlost"""
        return self.current_velocity


class WatchdogTimer:
    """
    Watchdog pro detekci ztráty řízeníOznač track jako zmeškaný
    """

    def __init__(self, timeout: float = 0.5):
        """
        Args:
            timeout: Timeout v sekundách
        """
        self.timeout = timeout
        self.last_update_time: Optional[float] = None
        self.triggered = False

    def feed(self):
        """Aktualizuj watchdog (krmení)"""
        self.last_update_time = time.time()
        self.triggered = False

    def check(self) -> bool:
        """
        Zkontroluj timeout

        Returns:
            True pokud timeout vypršel
        """
        if self.last_update_time is None:
            return False

        elapsed = time.time() - self.last_update_time

        if elapsed > self.timeout and not self.triggered:
            self.triggered = True
            logger.warning(f"Watchdog timeout ({elapsed:.2f}s)")
            return True

        return self.triggered

    def reset(self):
        """Reset watchdog"""
        self.last_update_time = None
        self.triggered = False

    def is_triggered(self) -> bool:
        """Je watchdog spuštěný?"""
        return self.triggered


class SpeedLimiter:
    """
    Omezovač rychlosti na základě bezpečnostních podmínek
    """

    def __init__(
        self,
        max_linear_speed: float = 0.6,
        max_angular_speed: float = 1.0
    ):
        """
        Args:
            max_linear_speed: Maximální lineární rychlost (m/s)
            max_angular_speed: Maximální angulární rychlost (rad/s)
        """
        self.max_linear_speed = max_linear_speed
        self.max_angular_speed = max_angular_speed

        self.speed_multiplier = 1.0

    def limit_velocity(
        self,
        linear: float,
        angular: float,
        safety_multiplier: float = 1.0
    ) -> tuple[float, float]:
        """
        Aplikuj limity rychlosti

        Args:
            linear: Požadovaná lineární rychlost
            angular: Požadovaná angulární rychlost
            safety_multiplier: Bezpečnostní multiplikátor (0-1)

        Returns:
            (omezená_lineární, omezená_angulární)
        """
        # Aplikuj safety multiplikátor
        effective_linear_limit = self.max_linear_speed * safety_multiplier * self.speed_multiplier
        effective_angular_limit = self.max_angular_speed * safety_multiplier * self.speed_multiplier

        # Saturace
        limited_linear = np.clip(linear, -effective_linear_limit, effective_linear_limit)
        limited_angular = np.clip(angular, -effective_angular_limit, effective_angular_limit)

        return limited_linear, limited_angular

    def set_speed_multiplier(self, multiplier: float):
        """
        Nastav globální speed multiplikátor

        Args:
            multiplier: Multiplikátor (0-1)
        """
        self.speed_multiplier = np.clip(multiplier, 0.0, 1.0)
        logger.info(f"Speed multiplikátor nastaven na {self.speed_multiplier:.2f}")

    def set_max_speeds(self, linear: Optional[float] = None, angular: Optional[float] = None):
        """Nastav maximální rychlosti"""
        if linear is not None:
            self.max_linear_speed = linear
        if angular is not None:
            self.max_angular_speed = angular
        logger.info(f"Max rychlosti: lin={self.max_linear_speed}, ang={self.max_angular_speed}")
