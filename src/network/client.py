"""
ZeroMQ komunikační vrstva pro ovládání robota
"""

import zmq
import zmq.asyncio
import asyncio
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
import time
import uuid
from loguru import logger
from collections import deque


@dataclass
class MotionCommand:
    """Příkaz pro pohyb robota"""
    linear_velocity: float  # m/s
    angular_velocity: float  # rad/s
    timestamp: int = 0
    command_id: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = int(time.time() * 1000)
        if not self.command_id:
            self.command_id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """Konverze na slovník"""
        return {
            'linear_velocity': self.linear_velocity,
            'angular_velocity': self.angular_velocity,
            'timestamp': self.timestamp,
            'command_id': self.command_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MotionCommand":
        """Vytvoření z slovníku"""
        return cls(
            linear_velocity=data['linear_velocity'],
            angular_velocity=data['angular_velocity'],
            timestamp=data.get('timestamp', 0),
            command_id=data.get('command_id', '')
        )


@dataclass
class Telemetry:
    """Telemetrická data z robota"""
    timestamp: int
    linear_velocity: float = 0.0
    angular_velocity: float = 0.0
    left_wheel_rpm: float = 0.0
    right_wheel_rpm: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0
    yaw: float = 0.0
    gyro_x: float = 0.0
    gyro_y: float = 0.0
    gyro_z: float = 0.0
    accel_x: float = 0.0
    accel_y: float = 0.0
    accel_z: float = 0.0
    ultrasonic_front: float = 0.0
    ultrasonic_left: float = 0.0
    ultrasonic_right: float = 0.0
    ultrasonic_back: float = 0.0
    battery_voltage: float = 0.0
    battery_current: float = 0.0
    battery_percentage: float = 100.0
    cpu_temperature: float = 0.0
    motor_temperature: float = 0.0
    robot_state: str = "idle"
    errors: list = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Telemetry":
        """Vytvoření z slovníku"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


class RobotClient:
    """
    ZeroMQ klient pro komunikaci s robotem
    """

    def __init__(
        self,
        robot_ip: str,
        command_port: int = 5555,
        telemetry_port: int = 5556,
        keepalive_interval: float = 1.0
    ):
        """
        Args:
            robot_ip: IP adresa robota
            command_port: Port pro odesílání příkazů (REQ)
            telemetry_port: Port pro příjem telemetrie (SUB)
            keepalive_interval: Interval keepalive v sekundách
        """
        self.robot_ip = robot_ip
        self.command_port = command_port
        self.telemetry_port = telemetry_port
        self.keepalive_interval = keepalive_interval

        self.context: Optional[zmq.asyncio.Context] = None
        self.command_socket: Optional[zmq.asyncio.Socket] = None
        self.telemetry_socket: Optional[zmq.asyncio.Socket] = None

        self.connected = False
        self.last_telemetry: Optional[Telemetry] = None
        self.last_telemetry_time: float = 0
        self.last_command_time: float = 0

        self.telemetry_callback: Optional[Callable[[Telemetry], None]] = None
        self.connection_lost_callback: Optional[Callable[[], None]] = None

        self._keepalive_task: Optional[asyncio.Task] = None
        self._telemetry_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

        # Latence tracking
        self.latency_history = deque(maxlen=100)
        self.avg_latency = 0.0

    async def connect(self) -> bool:
        """
        Připoj se k robotu

        Returns:
            True pokud úspěšné připojení
        """
        try:
            logger.info(f"Připojuji se k robotu na {self.robot_ip}")

            self.context = zmq.asyncio.Context()

            # Command socket (REQ/REP pattern)
            self.command_socket = self.context.socket(zmq.REQ)
            self.command_socket.setsockopt(zmq.LINGER, 0)
            self.command_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5s timeout
            self.command_socket.setsockopt(zmq.SNDTIMEO, 5000)
            command_addr = f"tcp://{self.robot_ip}:{self.command_port}"
            self.command_socket.connect(command_addr)
            logger.debug(f"Command socket připojen: {command_addr}")

            # Telemetry socket (SUB pattern)
            self.telemetry_socket = self.context.socket(zmq.SUB)
            self.telemetry_socket.setsockopt(zmq.SUBSCRIBE, b"")  # Subscribe na všechno
            self.telemetry_socket.setsockopt(zmq.RCVTIMEO, 3000)  # 3s timeout
            telemetry_addr = f"tcp://{self.robot_ip}:{self.telemetry_port}"
            self.telemetry_socket.connect(telemetry_addr)
            logger.debug(f"Telemetry socket připojen: {telemetry_addr}")

            # Test spojení
            test_success = await self._test_connection()
            if not test_success:
                await self.disconnect()
                return False

            self.connected = True
            self._stop_event.clear()

            # Spusť background tasks
            self._keepalive_task = asyncio.create_task(self._keepalive_loop())
            self._telemetry_task = asyncio.create_task(self._telemetry_loop())

            logger.success(f"Připojeno k robotu {self.robot_ip}")
            return True

        except Exception as e:
            logger.error(f"Chyba při připojování: {e}")
            await self.disconnect()
            return False

    async def disconnect(self):
        """Odpoj se od robota"""
        logger.info("Odpojuji se od robota")
        self.connected = False
        self._stop_event.set()

        # Zastav background tasks
        if self._keepalive_task:
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass

        if self._telemetry_task:
            self._telemetry_task.cancel()
            try:
                await self._telemetry_task
            except asyncio.CancelledError:
                pass

        # Zavři sockety
        if self.command_socket:
            self.command_socket.close()
        if self.telemetry_socket:
            self.telemetry_socket.close()

        # Zruš context
        if self.context:
            self.context.term()

        logger.info("Odpojeno")

    async def _test_connection(self) -> bool:
        """Test připojení odesláním heartbeat"""
        try:
            heartbeat = {
                'type': 'heartbeat',
                'timestamp': int(time.time() * 1000)
            }
            await self.command_socket.send_json(heartbeat)
            response = await self.command_socket.recv_json()
            return response.get('type') == 'heartbeat_ack'
        except Exception as e:
            logger.error(f"Test připojení selhal: {e}")
            return False

    async def send_motion_command(self, command: MotionCommand) -> bool:
        """
        Odešli příkaz pro pohyb

        Args:
            command: MotionCommand

        Returns:
            True pokud úspěšně odesláno
        """
        if not self.connected:
            logger.warning("Nelze odeslat příkaz, robot není připojen")
            return False

        try:
            start_time = time.perf_counter()

            message = {
                'type': 'motion_command',
                **command.to_dict()
            }

            await self.command_socket.send_json(message)
            response = await self.command_socket.recv_json()

            # Měř latenci
            latency = (time.perf_counter() - start_time) * 1000  # ms
            self.latency_history.append(latency)
            self.avg_latency = sum(self.latency_history) / len(self.latency_history)

            self.last_command_time = time.time()

            if response.get('status') == 'ok':
                logger.debug(f"Příkaz odeslán: lin={command.linear_velocity:.2f}, ang={command.angular_velocity:.2f}, latence={latency:.1f}ms")
                return True
            else:
                logger.warning(f"Příkaz odmítnut: {response.get('message')}")
                return False

        except zmq.Again:
            logger.error("Timeout při odesílání příkazu")
            await self._handle_connection_lost()
            return False
        except Exception as e:
            logger.error(f"Chyba při odesílání příkazu: {e}")
            return False

    async def send_emergency_stop(self, reason: str = "User request") -> bool:
        """
        Odešli nouzové zastavení

        Args:
            reason: Důvod zastavení

        Returns:
            True pokud úspěšně odesláno
        """
        if not self.connected:
            return False

        try:
            message = {
                'type': 'emergency_stop',
                'reason': reason,
                'timestamp': int(time.time() * 1000)
            }

            await self.command_socket.send_json(message)
            response = await self.command_socket.recv_json()

            logger.warning(f"Emergency stop odesláno: {reason}")
            return response.get('status') == 'ok'

        except Exception as e:
            logger.error(f"Chyba při emergency stop: {e}")
            return False

    async def _keepalive_loop(self):
        """Background loop pro keepalive"""
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(self.keepalive_interval)

                # Kontrola, zda nedošlo k timeoutu telemetrie
                time_since_telemetry = time.time() - self.last_telemetry_time
                if time_since_telemetry > 3.0 and self.last_telemetry_time > 0:
                    logger.warning(f"Telemetrie timeout ({time_since_telemetry:.1f}s)")
                    await self._handle_connection_lost()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Chyba v keepalive loop: {e}")

    async def _telemetry_loop(self):
        """Background loop pro příjem telemetrie"""
        while not self._stop_event.is_set():
            try:
                # Přijmi telemetrii
                message = await self.telemetry_socket.recv_json()

                if message.get('type') == 'telemetry':
                    telemetry = Telemetry.from_dict(message)
                    self.last_telemetry = telemetry
                    self.last_telemetry_time = time.time()

                    # Callback
                    if self.telemetry_callback:
                        try:
                            self.telemetry_callback(telemetry)
                        except Exception as e:
                            logger.error(f"Chyba v telemetry callback: {e}")

            except zmq.Again:
                # Timeout, zkus znovu
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Chyba v telemetry loop: {e}")
                await asyncio.sleep(0.1)

    async def _handle_connection_lost(self):
        """Zpracuj ztrátu připojení"""
        if self.connected:
            logger.error("Ztráta připojení k robotu")
            self.connected = False

            if self.connection_lost_callback:
                try:
                    self.connection_lost_callback()
                except Exception as e:
                    logger.error(f"Chyba v connection_lost callback: {e}")

    def set_telemetry_callback(self, callback: Callable[[Telemetry], None]):
        """Nastav callback pro telemetrii"""
        self.telemetry_callback = callback

    def set_connection_lost_callback(self, callback: Callable[[], None]):
        """Nastav callback pro ztrátu připojení"""
        self.connection_lost_callback = callback

    def get_latency(self) -> float:
        """Získej průměrnou latenci"""
        return self.avg_latency

    def is_connected(self) -> bool:
        """Je připojeno?"""
        return self.connected

    def get_last_telemetry(self) -> Optional[Telemetry]:
        """Získej poslední telemetrii"""
        return self.last_telemetry
