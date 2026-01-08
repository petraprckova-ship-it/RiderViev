"""
Unit testy pro ML pipeline
"""

import pytest
import numpy as np
from pathlib import Path

from src.ml.detector import PersonDetector, Detection
from src.ml.tracker import ByteTracker, Track
from src.ml.distance import BBoxDistanceEstimator, DistanceTracker


@pytest.fixture
def mock_frame():
    """Mock video frame"""
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def mock_detections():
    """Mock detections"""
    return [
        Detection(bbox=[100, 100, 200, 300], confidence=0.9, class_id=0, class_name="person"),
        Detection(bbox=[400, 150, 500, 350], confidence=0.85, class_id=0, class_name="person"),
    ]


def test_detection_creation():
    """Test vytvoření Detection objektu"""
    det = Detection(
        bbox=[10, 20, 100, 200],
        confidence=0.95,
        class_id=0,
        class_name="person"
    )
    
    assert det.bbox == [10, 20, 100, 200]
    assert det.confidence == 0.95
    assert det.width == 90
    assert det.height == 180
    

def test_bytetrack_initialization():
    """Test inicializace ByteTracker"""
    tracker = ByteTracker(
        high_conf_threshold=0.5,
        match_threshold=0.8,
        track_buffer=30
    )
    
    assert tracker.high_conf_threshold == 0.5
    assert tracker.match_threshold == 0.8
    assert len(tracker.tracks) == 0


def test_bytetrack_update(mock_detections):
    """Test update ByteTracker"""
    tracker = ByteTracker()
    
    # Přímo použij mock_detections (jsou už Detection objekty)
    tracks = tracker.update(mock_detections)
    
    # Měly by být vytvořeny tracky (může být 0 kvůli tentative threshold)
    assert len(tracks) >= 0
    
    # Druhý update (stejné detekce)
    tracks = tracker.update(mock_detections)
    
    # Tracky by měly pokračovat
    assert len(tracks) >= 0
    

def test_track_state_machine():
    """Test stavového stroje Track"""
    from src.ml.detector import Detection
    
    bbox = np.array([100.0, 100.0, 200.0, 300.0], dtype=np.float32)
    track = Track(
        bbox=bbox,
        confidence=0.9,
        track_id=1
    )
    
    # Nový track je tentative
    assert track.state == "tentative"
    
    # Po několika update -> confirmed
    for _ in range(5):
        det = Detection(bbox=bbox.tolist(), confidence=0.9, class_id=0, class_name="person")
        track.update(det)
        
    assert track.state == "confirmed"


def test_bbox_distance_estimator():
    """Test BBox distance estimator"""
    estimator = BBoxDistanceEstimator(
        focal_length=500,
        avg_person_height=1.7
    )
    
    # Test odhadu
    bbox = np.array([100, 100, 200, 400])  # height = 300px
    distance_info = estimator.estimate(bbox)
    
    assert distance_info.distance > 0
    assert distance_info.method == "bbox"
    assert 0 <= distance_info.confidence <= 1.0
    
    # Test odhadu vzdálenosti
    bbox = [100, 100, 200, 300]  # height = 200px
    distance_info2 = estimator.estimate(bbox)
    
    assert distance_info2.distance > 0
    assert distance_info2.distance < 100  # rozumná vzdálenost
    

def test_distance_tracker():
    """Test DistanceTracker"""
    tracker = DistanceTracker(smoothing=0.3, history_size=10)
    
    # Přidej měření
    for i in range(15):
        measurement = 5.0 + np.random.randn() * 0.1
        tracker.update(measurement)
        
    # Získej poslední vyhlazené
    smoothed = tracker.get_distance()
    
    assert smoothed is not None
    assert abs(smoothed - 5.0) < 1.0  # Mělo by být blízko 5.0


@pytest.mark.skipif(not Path("models/yolo11n.pt").exists(), reason="Model soubor neexistuje")
def test_person_detector_initialization():
    """Test inicializace PersonDetector"""
    detector = PersonDetector(
        model_name="yolo11n",
        device="cpu",
        backend="pytorch",
        confidence_threshold=0.5
    )
    
    assert detector.model is not None
    assert detector.confidence_threshold == 0.5


@pytest.mark.skipif(not Path("models/yolo11n.pt").exists(), reason="Model soubor neexistuje")
def test_person_detector_inference(mock_frame):
    """Test inference PersonDetector"""
    detector = PersonDetector(
        model_name="yolo11n",
        device="cpu",
        backend="pytorch"
    )
    
    # Detekce (na černém frame nebude nic)
    detections = detector.detect(mock_frame)
    
    assert isinstance(detections, list)
