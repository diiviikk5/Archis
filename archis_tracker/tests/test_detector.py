"""Unit tests for optical beacon detection and sub-pixel centroiding."""
import pytest
import numpy as np
from archis_tracker.core.detector import BeaconDetector


def test_beacon_detection_clean():
    det = BeaconDetector()
    frame = np.zeros((480, 640), dtype=np.uint8)
    
    # Place a 10x10 spot at (342, 218)
    frame[213:223, 337:347] = 255
    
    res = det.detect(frame)
    assert res.detected, "Should detect bright beacon spot"
    assert abs(res.x - 342.0) < 1.0, f"Expected X near 342, got {res.x}"
    assert abs(res.y - 218.0) < 1.0, f"Expected Y near 218, got {res.y}"
    assert res.confidence > 0.5


def test_detection_under_gaussian_noise():
    det = BeaconDetector()
    frame = np.random.normal(20, 5, (480, 640)).clip(0, 255).astype(np.uint8)
    
    # Place 12x12 spot at (250, 180)
    frame[174:186, 244:256] = 250
    
    res = det.detect(frame)
    assert res.detected, "Should detect beacon under moderate background noise"
    assert abs(res.x - 250.0) < 1.5
    assert abs(res.y - 180.0) < 1.5
