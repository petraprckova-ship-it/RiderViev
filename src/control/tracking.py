"""
Hlavní řídící systém pro sledování osob
"""

import numpy as np
from enum import Enum
from typing import Optional
from loguru import logger
import time

from ..ml.tracker import Track
from ..ml.distance import DistanceInfo, ZoneClassifier
from .pid import DualPIDController, VelocityProfiler, WatchdogTimer, SpeedLimiter, PIDConfig


class TrackingMode(Enum):
    """Režimy sledování"""
    IDLE = "idle"
    SEARCHING = "searching"
    LOCKED = "locked"
    LOST_TEMP = "lost_temp"
    LOST_PERM = "lost_perm"
    MANUAL = "manual"
    EMERGENCY_STOP = "emergency_stop"


class PersonTrackingController:
    """
    Hlavní controller pro autonomní sledování osob
    """

    def __init__(
        self,
        linear_pid_config: PIDConfig,
        angular_pid_config: PIDConfig,
        max_linear_speed: float = 0.6,
        max_angular_speed: float = 1.0,
        max_acceleration: float = 0.4,
        max_deceleration: float = 0.5,
        target_distance_min: float = 1.0,
        target_distance_max: float = 2.5,
        frame_center: tuple = (320, 240)
    ):
        """
        Args:
            linear_pid_config: Konfigurace lineárního PID
            angular_pid_config: Konfigurace angulárního PID
            max_linear_speed: Max lineární rychlost (m/s)
            max_angular_speed: Max angulární rychlost (rad/s)
            max_acceleration: Max zrychlení (m/s²)
            max_deceleration: Max zpomalení (m/s²)
            target_distance_min: Min cílová vzdálenost (m)
            target_distance_max: Max cílová vzdálenost (m)
            frame_center: Střed snímku (x, y)
        """
        # PID regulátory
        self.pid_controller = DualPIDController(linear_pid_config, angular_pid_config)

        # Velocity profiler
        self.linear_profiler = VelocityProfiler(max_acceleration, max_deceleration)
        self.angular_profiler = VelocityProfiler(max_acceleration * 2, max_deceleration * 2)

        # Speed limiter
        self.speed_limiter = SpeedLimiter(max_linear_speed, max_angular_speed)

        # Watchdog
        self.watchdog = WatchdogTimer(timeout=0.5)

        # Zone classifier
        self.zone_classifier = ZoneClassifier(
            red_zone=0.30,
            yellow_zone=0.60,
            target_min=target_distance_min,
            target_max=target_distance_max
        )

        # Stav
        self.mode = TrackingMode.IDLE
        self.frame_center = frame_center
        self.frame_lost_count = 0
        self.frame_locked_count = 0

        # Timing
        self.last_update_time = time.time()

        # Aktuální cíl
        self.current_target: Optional[Track] = None
        self.current_distance: Optional[DistanceInfo] = None

        # Výstupy
        self.command_linear_velocity = 0.0
        self.command_angular_velocity = 0.0

    def update(
        self,
        target_track: Optional[Track],
        distance_info: Optional[DistanceInfo],
        obstacle_detected: bool = False
    ) -> tuple[float, float]:
        """
        Hlavní update funkce

        Args:
            target_track: Sledovaný track (None pokud není detekce)
            distance_info: Informace o vzdálenosti
            obstacle_detected: Je detekována překážka?

        Returns:
            (linear_velocity, angular_velocity)
        """
        current_time = time.time()
        dt = current_time - self.last_update_time
        self.last_update_time = current_time

        # Aktualizuj watchdog
        self.watchdog.feed()

        # Update state machine
        self._update_state_machine(target_track, distance_info)

        # Vypočítej příkazy podle režimu
        if self.mode == TrackingMode.LOCKED and target_track and distance_info:
            linear_cmd, angular_cmd = self._compute_tracking_commands(
                target_track, distance_info, dt
            )
        elif self.mode == TrackingMode.SEARCHING:
            # Pomalé otáčení pro hledání
            linear_cmd = 0.0
            angular_cmd = 0.3  # Otáčej se pomalu
        elif self.mode == TrackingMode.LOST_TEMP and self.current_target:
            # Použij predikci z Kalman filtru
            predicted_bbox = self.current_target.get_predicted_bbox(steps=5)
            linear_cmd, angular_cmd = self._compute_commands_from_bbox(
                predicted_bbox, dt, factor=0.5
            )
        else:
            # Idle, Manual, Emergency Stop
            linear_cmd = 0.0
            angular_cmd = 0.0

        # Emergency stop při překážce
        if obstacle_detected:
            logger.warning("Překážka detekována - zastavuji")
            linear_cmd = 0.0
            angular_cmd = 0.0
            self.mode = TrackingMode.EMERGENCY_STOP

        # Aplikuj velocity profiling pro plynulé pohyby
        smooth_linear = self.linear_profiler.update(linear_cmd, dt)
        smooth_angular = self.angular_profiler.update(angular_cmd, dt)

        # Získej safety multiplikátor ze zóny
        safety_multiplier = 1.0
        if distance_info:
            safety_multiplier = self.zone_classifier.get_speed_multiplier(distance_info.distance)

        # Aplikuj speed limiter
        final_linear, final_angular = self.speed_limiter.limit_velocity(
            smooth_linear, smooth_angular, safety_multiplier
        )

        self.command_linear_velocity = final_linear
        self.command_angular_velocity = final_angular

        return final_linear, final_angular

    def _update_state_machine(
        self,
        target_track: Optional[Track],
        distance_info: Optional[DistanceInfo]
    ):
        """Aktualizuj state machine"""
        # Uložení aktuálního cíle
        if target_track:
            self.current_target = target_track
            self.current_distance = distance_info

        # Transitions
        if target_track is None:
            # Žádná detekce
            self.frame_lost_count += 1
            self.frame_locked_count = 0

            if self.mode == TrackingMode.LOCKED:
                self.mode = TrackingMode.LOST_TEMP
                logger.info("Cíl dočasně ztracen")

            elif self.mode == TrackingMode.LOST_TEMP:
                if self.frame_lost_count > 60:  # 2 sekundy @ 30 FPS
                    self.mode = TrackingMode.LOST_PERM
                    logger.warning("Cíl permanentně ztracen")

            elif self.mode == TrackingMode.LOST_PERM:
                if self.frame_lost_count > 150:  # 5 sekund
                    self.mode = TrackingMode.SEARCHING
                    logger.info("Vstupuji do režimu hledání")

        else:
            # Máme detekci
            self.frame_lost_count = 0
            self.frame_locked_count += 1

            if self.mode in [TrackingMode.IDLE, TrackingMode.SEARCHING, TrackingMode.LOST_TEMP, TrackingMode.LOST_PERM]:
                if self.frame_locked_count >= 3:  # 3 po sobě jdoucí snímky
                    self.mode = TrackingMode.LOCKED
                    logger.success("Cíl zamčen!")
                    self.pid_controller.reset()

    def _compute_tracking_commands(
        self,
        target_track: Track,
        distance_info: DistanceInfo,
        dt: float
    ) -> tuple[float, float]:
        """
        Vypočítej příkazy pro sledování

        Args:
            target_track: Track k sledování
            distance_info: Vzdálenost
            dt: Časový krok

        Returns:
            (linear_cmd, angular_cmd)
        """
        # 1. Lineární rychlost - řídíme vzdálenost
        target_distance = (self.zone_classifier.target_min + self.zone_classifier.target_max) / 2
        distance_error = distance_info.distance - target_distance

        # Použij proporcionální řízení pro vzdálenost
        linear_cmd = distance_error * 0.5  # Gain pro vzdálenost

        # 2. Angulární rychlost - řídíme horizontální pozici
        bbox_center_x = (target_track.bbox[0] + target_track.bbox[2]) / 2
        horizontal_error = bbox_center_x - self.frame_center[0]

        # Normalizuj chybu (-1 až 1)
        normalized_error = horizontal_error / self.frame_center[0]

        # Použij proporcionální řízení pro otáčení
        angular_cmd = normalized_error * 1.5  # Gain pro otáčení

        return linear_cmd, angular_cmd

    def _compute_commands_from_bbox(
        self,
        bbox: np.ndarray,
        dt: float,
        factor: float = 1.0
    ) -> tuple[float, float]:
        """
        Vypočítej příkazy z bbox (pro predikci)

        Args:
            bbox: [x1, y1, x2, y2]
            dt: Časový krok
            factor: Multiplikátor (pro oslabení při predikci)

        Returns:
            (linear_cmd, angular_cmd)
        """
        bbox_center_x = (bbox[0] + bbox[2]) / 2
        horizontal_error = bbox_center_x - self.frame_center[0]
        normalized_error = horizontal_error / self.frame_center[0]

        # Pouze otáčení při predikci (žádný pohyb vpřed)
        linear_cmd = 0.0
        angular_cmd = normalized_error * 1.0 * factor

        return linear_cmd, angular_cmd

    def set_mode(self, mode: TrackingMode):
        """Manuální nastavení režimu"""
        logger.info(f"Režim změněn: {self.mode.value} -> {mode.value}")
        self.mode = mode

        if mode == TrackingMode.IDLE:
            self.linear_profiler.reset()
            self.angular_profiler.reset()
            self.pid_controller.reset()

    def emergency_stop(self):
        """Nouzové zastavení"""
        logger.error("EMERGENCY STOP aktivován")
        self.mode = TrackingMode.EMERGENCY_STOP
        self.command_linear_velocity = 0.0
        self.command_angular_velocity = 0.0
        self.linear_profiler.reset()
        self.angular_profiler.reset()

    def resume(self):
        """Obnovení po emergency stop"""
        if self.mode == TrackingMode.EMERGENCY_STOP:
            logger.info("Obnovuji z emergency stop")
            self.mode = TrackingMode.IDLE

    def set_speed_profile(
        self,
        max_linear: float,
        max_angular: float,
        acceleration: float,
        deceleration: float
    ):
        """
        Nastav rychlostní profil

        Args:
            max_linear: Max lineární rychlost
            max_angular: Max angulární rychlost
            acceleration: Zrychlení
            deceleration: Zpomalení
        """
        self.speed_limiter.set_max_speeds(max_linear, max_angular)
        self.linear_profiler.max_acceleration = acceleration
        self.linear_profiler.max_deceleration = deceleration
        self.angular_profiler.max_acceleration = acceleration * 2
        self.angular_profiler.max_deceleration = deceleration * 2
        logger.info(f"Rychlostní profil nastaven: lin={max_linear}, ang={max_angular}")

    def set_pid_gains(
        self,
        linear_kp: Optional[float] = None,
        linear_ki: Optional[float] = None,
        linear_kd: Optional[float] = None,
        angular_kp: Optional[float] = None,
        angular_ki: Optional[float] = None,
        angular_kd: Optional[float] = None
    ):
        """Nastav PID zisky"""
        if any([linear_kp, linear_ki, linear_kd]):
            self.pid_controller.linear_pid.set_gains(linear_kp, linear_ki, linear_kd)

        if any([angular_kp, angular_ki, angular_kd]):
            self.pid_controller.angular_pid.set_gains(angular_kp, angular_ki, angular_kd)

    def get_status(self) -> dict:
        """Získej stav controlleru"""
        return {
            'mode': self.mode.value,
            'command_linear': self.command_linear_velocity,
            'command_angular': self.command_angular_velocity,
            'frame_lost_count': self.frame_lost_count,
            'frame_locked_count': self.frame_locked_count,
            'has_target': self.current_target is not None,
            'target_distance': self.current_distance.distance if self.current_distance else None
        }
