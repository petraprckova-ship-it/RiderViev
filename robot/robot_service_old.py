#!/usr/bin/env python3
"""
Robot-side service pro Yahboom Rider Pi CM4
Běží na Raspberry Pi a komunikuje s desktop aplikací
"""

import sys
import asyncio
import time
import zmq
import zmq.asyncio
from pathlib import Path
from loguru import logger
from typing import Optional
import json


class RobotHardware:
    """
    Rozhraní pro Yahboom Rider Pi CM4 hardware
    """

    def __init__(self):
        """Inicializace hardware rozhraní"""
        self.initialized = False

        try:
            # Import Yahboom knihoven (specifické pro platformu)
            # import RiderLib  # Yahboom knihovna
            logger.info("Inicializuji hardware...")

            # Inicializace motorů, IMU, senzorů
            # TODO: Implementovat skutečnou inicializaci

            self.initialized = True
            logger.success("Hardware inicializován")

        except Exception as e:
            logger.error(f"Chyba při inicializaci hardware: {e}")
            self.initialized = False

    def set_motor_speeds(self, linear_velocity: float, angular_velocity: float):
        """
        Nastav rychlosti motorů

        Args:
            linear_velocity: Lineární rychlost (m/s)
            angular_velocity: Angulární rychlost (rad/s)
        """
        try:
            # Převod na PWM hodnoty pro levý a pravý motor
            # Yahboom Rider používá diferenciální řízení

            # Zjednodušený výpočet:
            # left_speed = linear - angular * wheel_base / 2
            # right_speed = linear + angular * wheel_base / 2

            wheel_base = 0.15  # metry, vzdálenost mezi koly

            left_speed = linear_velocity - angular_velocity * wheel_base / 2
            right_speed = linear_velocity + angular_velocity * wheel_base / 2

            # Mapování na PWM (-100 až 100)
            max_speed = 1.0  # m/s
            left_pwm = int((left_speed / max_speed) * 100)
            right_pwm = int((right_speed / max_speed) * 100)

            # Saturace
            left_pwm = max(-100, min(100, left_pwm))
            right_pwm = max(-100, min(100, right_pwm))

            logger.debug(f"Motors: L={left_pwm}, R={right_pwm}")

            # TODO: Skutečné nastavení motorů
            # RiderLib.set_motor(left_pwm, right_pwm)

        except Exception as e:
            logger.error(f"Chyba při nastavení motorů: {e}")

    def read_imu(self) -> dict:
        """
        Načti data z IMU

        Returns:
            Dict s pitch, roll, yaw, gyro, accel
        """
        # TODO: Skutečné čtení z IMU
        return {
            'pitch': 0.0,
            'roll': 0.0,
            'yaw': 0.0,
            'gyro_x': 0.0,
            'gyro_y': 0.0,
            'gyro_z': 0.0,
            'accel_x': 0.0,
            'accel_y': 0.0,
            'accel_z': 9.81
        }

    def read_ultrasonic_sensors(self) -> dict:
        """
        Načti vzdálenosti z ultrazvukových senzorů

        Returns:
            Dict se vzdálenostmi v cm
        """
        # TODO: Skutečné čtení ze senzorů
        return {
            'front': 100.0,
            'left': 100.0,
            'right': 100.0,
            'back': 100.0
        }

    def read_battery(self) -> dict:
        """
        Načti stav baterie

        Returns:
            Dict s voltage, current, percentage
        """
        # TODO: Skutečné čtení baterie
        return {
            'voltage': 12.0,
            'current': 0.5,
            'percentage': 85.0
        }

    def read_temperature(self) -> dict:
        """
        Načti teploty

        Returns:
            Dict s teplotami
        """
        # TODO: Skutečné čtení teplot
        return {
            'cpu': 45.0,
            'motor': 40.0
        }

    def emergency_stop(self):
        """Nouzové zastavení všech motorů"""
        try:
            self.set_motor_speeds(0.0, 0.0)
            logger.warning("Emergency stop executed")
        except Exception as e:
            logger.error(f"Emergency stop failed: {e}")

    def shutdown(self):
        """Vypnutí hardware"""
        try:
            self.emergency_stop()
            # TODO: Cleanup
            logger.info("Hardware shutdown")
        except Exception as e:
            logger.error(f"Shutdown error: {e}")


class RobotServer:
    """
    ZeroMQ server běžící na robotu
    """

    def __init__(
        self,
        command_port: int = 5555,
        telemetry_port: int = 5556
    ):
        """
        Args:
            command_port: Port pro příjem příkazů
            telemetry_port: Port pro vysílání telemetrie
        """
        self.command_port = command_port
        self.telemetry_port = telemetry_port

        self.context: Optional[zmq.asyncio.Context] = None
        self.command_socket: Optional[zmq.asyncio.Socket] = None
        self.telemetry_socket: Optional[zmq.asyncio.Socket] = None

        self.hardware = RobotHardware()
        self.running = False

        self._command_task: Optional[asyncio.Task] = None
        self._telemetry_task: Optional[asyncio.Task] = None

        # Watchdog
        self.last_command_time = time.time()
        self.watchdog_timeout = 0.5  # sekundy

        logger.info("Robot server inicializován")

    async def start(self):
        """Spuštění serveru"""
        try:
            logger.info("Spouštím robot server...")

            self.context = zmq.asyncio.Context()

            # Command socket (REP)
            self.command_socket = self.context.socket(zmq.REP)
            self.command_socket.bind(f"tcp://*:{self.command_port}")
            logger.info(f"Command socket: tcp://*:{self.command_port}")

            # Telemetry socket (PUB)
            self.telemetry_socket = self.context.socket(zmq.PUB)
            self.telemetry_socket.bind(f"tcp://*:{self.telemetry_port}")
            logger.info(f"Telemetry socket: tcp://*:{self.telemetry_port}")

            self.running = True

            # Spusť background tasks
            self._command_task = asyncio.create_task(self._command_loop())
            self._telemetry_task = asyncio.create_task(self._telemetry_loop())
            watchdog_task = asyncio.create_task(self._watchdog_loop())

            logger.success("Robot server běží")

            # Čekej na ukončení
            await asyncio.gather(
                self._command_task,
                self._telemetry_task,
                watchdog_task
            )

        except Exception as e:
            logger.exception(f"Chyba při spuštění serveru: {e}")
            await self.stop()

    async def stop(self):
        """Zastavení serveru"""
        logger.info("Zastavuji robot server...")
        self.running = False

        # Nouzové zastavení
        self.hardware.emergency_stop()

        # Zastav tasks
        if self._command_task:
            self._command_task.cancel()
        if self._telemetry_task:
            self._telemetry_task.cancel()

        # Zavři sockety
        if self.command_socket:
            self.command_socket.close()
        if self.telemetry_socket:
            self.telemetry_socket.close()

        # Zruš context
        if self.context:
            self.context.term()

        # Vypni hardware
        self.hardware.shutdown()

        logger.info("Robot server zastaven")

    async def _command_loop(self):
        """Loop pro příjem a zpracování příkazů"""
        while self.running:
            try:
                # Přijmi příkaz
                message = await self.command_socket.recv_json()

                msg_type = message.get('type')

                if msg_type == 'heartbeat':
                    # Heartbeat
                    response = {'type': 'heartbeat_ack', 'timestamp': int(time.time() * 1000)}
                    await self.command_socket.send_json(response)

                elif msg_type == 'motion_command':
                    # Příkaz pro pohyb
                    linear = message.get('linear_velocity', 0.0)
                    angular = message.get('angular_velocity', 0.0)

                    self.hardware.set_motor_speeds(linear, angular)
                    self.last_command_time = time.time()

                    response = {'status': 'ok', 'timestamp': int(time.time() * 1000)}
                    await self.command_socket.send_json(response)

                    logger.debug(f"Motion command: lin={linear:.2f}, ang={angular:.2f}")

                elif msg_type == 'emergency_stop':
                    # Nouzové zastavení
                    self.hardware.emergency_stop()

                    response = {'status': 'ok', 'timestamp': int(time.time() * 1000)}
                    await self.command_socket.send_json(response)

                    logger.warning("Emergency stop received")

                else:
                    logger.warning(f"Neznámý typ zprávy: {msg_type}")
                    response = {'status': 'error', 'message': 'Unknown message type'}
                    await self.command_socket.send_json(response)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Chyba v command loop: {e}")
                await asyncio.sleep(0.1)

    async def _telemetry_loop(self):
        """Loop pro vysílání telemetrie"""
        while self.running:
            try:
                # Načti telemetrii
                imu_data = self.hardware.read_imu()
                ultrasonic_data = self.hardware.read_ultrasonic_sensors()
                battery_data = self.hardware.read_battery()
                temp_data = self.hardware.read_temperature()

                # Sestav zprávu
                telemetry = {
                    'type': 'telemetry',
                    'timestamp': int(time.time() * 1000),
                    'linear_velocity': 0.0,  # TODO: Skutečná hodnota
                    'angular_velocity': 0.0,
                    **imu_data,
                    'ultrasonic_front': ultrasonic_data['front'],
                    'ultrasonic_left': ultrasonic_data['left'],
                    'ultrasonic_right': ultrasonic_data['right'],
                    'ultrasonic_back': ultrasonic_data['back'],
                    **battery_data,
                    **temp_data,
                    'robot_state': 'idle' if time.time() - self.last_command_time > 1.0 else 'moving',
                    'errors': []
                }

                # Odešli telemetrii
                await self.telemetry_socket.send_json(telemetry)

                # Frekvence 20 Hz
                await asyncio.sleep(0.05)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Chyba v telemetry loop: {e}")
                await asyncio.sleep(0.1)

    async def _watchdog_loop(self):
        """Watchdog pro detekci ztráty spojení"""
        while self.running:
            try:
                await asyncio.sleep(0.1)

                # Kontrola watchdog
                elapsed = time.time() - self.last_command_time
                if elapsed > self.watchdog_timeout:
                    # Timeout - zastav motory
                    self.hardware.emergency_stop()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Chyba v watchdog loop: {e}")


def setup_logging():
    """Nastavení logování"""
    logger.remove()

    # Console logger
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
        colorize=True
    )

    # File logger
    log_dir = Path("/var/log/person-tracker")
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_dir / "robot_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="DEBUG",
        rotation="00:00",
        retention="7 days",
        compression="zip"
    )


async def main():
    """Hlavní funkce"""
    setup_logging()

    logger.info("=" * 60)
    logger.info("Person Tracker Robot Service")
    logger.info("=" * 60)

    server = RobotServer()

    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Přerušeno uživatelem")
    except Exception as e:
        logger.exception(f"Kritická chyba: {e}")
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
