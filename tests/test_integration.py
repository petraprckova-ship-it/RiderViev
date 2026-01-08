"""
Integrační testy
"""

import pytest
import asyncio
import numpy as np
from pathlib import Path

from src.config import Config, init_config
from src.network.client import RobotClient
from src.control.tracking import PersonTrackingController


@pytest.mark.asyncio
async def test_network_client_mock():
    """Test network clienta (mock)"""
    # Mock server není nutný, jen test inicializace
    client = RobotClient(robot_ip="127.0.0.1")
    
    # Test připojení by mělo selhat (žádný server)
    # Ale klient by měl být validní objekt
    assert client is not None
    

@pytest.mark.asyncio
async def test_tracking_controller_integration():
    """Integrační test tracking kontroleru"""
    from src.control.pid import PIDConfig
    config = Config()
    
    controller = PersonTrackingController(
        linear_pid_config=config.control.pid['linear'],
        angular_pid_config=config.control.pid['angular']
    )
    
    # Vytvoř testovací track a distance info
    from src.ml.tracker import Track
    from src.ml.distance import DistanceInfo
    track = Track(track_id=1, bbox=np.array([100, 100, 200, 300]), confidence=0.9)
    dist_info = DistanceInfo(distance=2.0, method="bbox", confidence=0.8)
    
    # Update
    linear, angular = controller.update(track, dist_info)
    
    # Mělo by být OK
    assert isinstance(linear, float)
    assert isinstance(angular, float)


def test_config_to_controller_integration():
    """Test integrace config -> controller"""
    config_path = Path("config/default_config.yaml")
    
    if not config_path.exists():
        pytest.skip("Config soubor neexistuje")
        
    config = init_config(str(config_path))
    
    # Vytvoř controller s configem
    from src.control.pid import PIDConfig
    controller = PersonTrackingController(
        linear_pid_config=config.control.pid['linear'],
        angular_pid_config=config.control.pid['angular']
    )
    
    # Zkontroluj, že parametry jsou z configu
    assert config.control.pid['linear'].kp > 0
    assert config.control.frequency > 0
    

@pytest.mark.skipif(not Path("models/yolo11n.pt").exists(), reason="Model neexistuje")
def test_full_pipeline_integration():
    """Test kompletní ML pipeline"""
    from src.ml.detector import PersonDetector
    from src.ml.tracker import ByteTracker
    from src.ml.distance import BBoxDistanceEstimator
    
    # Inicializace
    detector = PersonDetector(model_name="yolo11n", device="cpu", backend="pytorch")
    tracker = ByteTracker()
    distance_estimator = BBoxDistanceEstimator()
    
    # Testovací frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Detekce
    detections = detector.detect(frame)
    
    # Tracking
    tracks = tracker.update(detections)
    
    # Distance estimation
    for track in tracks:
        distance = distance_estimator.estimate(track.bbox)
        assert distance > 0
        
    # Mělo projít bez chyby
    assert True
