#!/usr/bin/env python3
"""
Robot Service - běží na Raspberry Pi a ovládá Yahboom hardware
"""

import asyncio
import zmq.asyncio
from loguru import logger
import time
import json
import sys
from pathlib import Path

# Přidej cestu k driveru
sys.path.insert(0, str(Path(__file__).parent))

from yahboom_driver import YahboomRiderDriver


class RobotServer:
    """ZeroMQ server pro příjem příkazů"""
    
    def __init__(self, command_port: int = 5555, telemetry_port: int = 5556, mock_mode: bool = False):
        """
        Args:
            command_port: Port pro příjem příkazů (REP)
            telemetry_port: Port pro vysílání telemetrie (PUB)
            mock_mode: True pro testování bez hardware
        """
        self.command_port = command_port
        self.telemetry_port = telemetry_port
        self.mock_mode = mock_mode
        
        # Hardware driver
        self.driver = YahboomRiderDriver(mock_mode=mock_mode)
        
        # ZeroMQ context
        self.context = zmq.asyncio.Context()
        self.command_socket = None
        self.telemetry_socket = None
        
        # Běží?
        self.is_running = False
        
        # Watchdog
        self.last_command_time = time.time()
        self.watchdog_timeout = 0.5  # 500ms
        
        logger.info(f"RobotServer inicializován (mock={mock_mode})")
        
    async def start(self):
        """Spuštění serveru"""
        logger.info("Spouštím robot server...")
        
        # Command socket (REP)
        self.command_socket = self.context.socket(zmq.REP)
        self.command_socket.bind(f"tcp://*:{self.command_port}")
        logger.info(f"Command socket: tcp://*:{self.command_port}")
        
        # Telemetry socket (PUB)
        self.telemetry_socket = self.context.socket(zmq.PUB)
        self.telemetry_socket.bind(f"tcp://*:{self.telemetry_port}")
        logger.info(f"Telemetry socket: tcp://*:{self.telemetry_port}")
        
        self.is_running = True
        
        # Spusť smyčky
        await asyncio.gather(
            self._command_loop(),
            self._telemetry_loop(),
            self._watchdog_loop()
        )
        
    async def stop(self):
        """Zastavení serveru"""
        logger.info("Zastavuji robot server...")
        
        self.is_running = False
        
        # Zastav motory
        self.driver.stop()
        
        # Zavři sockety
        if self.command_socket:
            self.command_socket.close()
        if self.telemetry_socket:
            self.telemetry_socket.close()
            
        self.context.term()
        
    async def _command_loop(self):
        """Smyčka pro příjem příkazů"""
        logger.info("Command loop spuštěna")
        
        while self.is_running:
            try:
                # Čekej na příkaz (s timeoutem)
                if await self.command_socket.poll(timeout=100):
                    message = await self.command_socket.recv_json()
                    
                    # Zpracuj příkaz
                    response = await self._handle_command(message)
                    
                    # Pošli odpověď
                    await self.command_socket.send_json(response)
                    
                    # Aktualizuj watchdog
                    self.last_command_time = time.time()
                    
            except Exception as e:
                logger.error(f"Chyba v command loop: {e}")
                # Pošli error response
                try:
                    await self.command_socket.send_json({'status': 'error', 'message': str(e)})
                except:
                    pass
                    
            await asyncio.sleep(0.001)  # 1ms
            
    async def _handle_command(self, message: dict) -> dict:
        """
        Zpracování příkazu
        
        Args:
            message: {'type': 'motion', 'linear': 0.5, 'angular': 0.0, ...}
            
        Returns:
            Response dict
        """
        cmd_type = message.get('type')
        
        if cmd_type == 'motion':
            # Motion command
            linear = message.get('linear', 0.0)
            angular = message.get('angular', 0.0)
            
            self.driver.set_velocity(linear, angular)
            
            return {
                'status': 'ok',
                'timestamp': time.time()
            }
            
        elif cmd_type == 'stop':
            # Emergency stop
            self.driver.stop()
            
            return {
                'status': 'ok',
                'message': 'Emergency stop executed'
            }
            
        elif cmd_type == 'led':
            # LED control
            r = message.get('r', 0)
            g = message.get('g', 0)
            b = message.get('b', 0)
            
            self.driver.set_rgb_led(r, g, b)
            
            return {'status': 'ok'}
            
        elif cmd_type == 'servo':
            # Servo control
            pan = message.get('pan', 90)
            tilt = message.get('tilt', 90)
            
            self.driver.set_servo_angles(pan, tilt)
            
            return {'status': 'ok'}
            
        elif cmd_type == 'ping':
            # Keep-alive ping
            return {
                'status': 'ok',
                'timestamp': time.time()
            }
            
        else:
            return {
                'status': 'error',
                'message': f'Unknown command type: {cmd_type}'
            }
            
    async def _telemetry_loop(self):
        """Smyčka pro vysílání telemetrie"""
        logger.info("Telemetry loop spuštěna")
        
        while self.is_running:
            try:
                # Získej telemetrii
                telemetry = self.driver.get_telemetry()
                
                # Přidej typ zprávy
                telemetry['type'] = 'telemetry'
                
                # Pošli přes PUB socket
                await self.telemetry_socket.send_json(telemetry)
                
            except Exception as e:
                logger.error(f"Chyba v telemetry loop: {e}")
                
            # 20 Hz (50ms)
            await asyncio.sleep(0.05)
            
    async def _watchdog_loop(self):
        """Watchdog timer - zastaví motory pokud nepřijde příkaz"""
        logger.info("Watchdog loop spuštěna")
        
        while self.is_running:
            try:
                elapsed = time.time() - self.last_command_time
                
                if elapsed > self.watchdog_timeout:
                    # Timeout - zastav motory
                    self.driver.stop()
                    logger.warning("Watchdog timeout - motory zastaveny")
                    
                    # Reset timer (aby nelogoval pořád)
                    self.last_command_time = time.time()
                    
            except Exception as e:
                logger.error(f"Chyba v watchdog loop: {e}")
                
            # Check každých 100ms
            await asyncio.sleep(0.1)


async def main():
    """Main funkce"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Robot Service pro Yahboom Rider")
    parser.add_argument('--command-port', type=int, default=5555, help='Port pro příkazy')
    parser.add_argument('--telemetry-port', type=int, default=5556, help='Port pro telemetrii')
    parser.add_argument('--mock', action='store_true', help='Mock režim (bez hardware)')
    
    args = parser.parse_args()
    
    # Nastavení logování
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    # Log file
    logger.add(
        "/var/log/person-tracker/robot_service.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG"
    )
    
    # Vytvoř server
    server = RobotServer(
        command_port=args.command_port,
        telemetry_port=args.telemetry_port,
        mock_mode=args.mock
    )
    
    try:
        # Spusť server
        await server.start()
        
    except KeyboardInterrupt:
        logger.info("Přijat SIGINT, ukončuji...")
        
    except Exception as e:
        logger.error(f"Neočekávaná chyba: {e}")
        
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
