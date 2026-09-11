import pytest
import numpy as np
from archis_tracker.core.ai_detector import NanoSpotDetector
from archis_tracker.core.detector import BeaconDetector
from archis_tracker.core.config import DetectorConfig, TrackingAlgorithm


def test_ai_detector_initialization():
    detector = NanoSpotDetector()
    assert detector.is_loaded is True
    assert detector.net is not None


def test_ai_detector_beacon_spot():
    detector = NanoSpotDetector()
    patch = np.zeros((64, 64), dtype=np.uint8)
    y, x = np.ogrid[:64, :64]
    # Circular optical spot at (34.2, 28.7)
    spot = 220.0 * np.exp(-((x - 34.2)**2 + (y - 28.7)**2) / (2 * 2.5**2))
    patch = np.clip(spot + 15.0, 0, 255).astype(np.uint8)

    detected, px, py, conf, is_decoy, heatmap = detector.detect_spot(patch, min_confidence=0.50)
    assert detected is True
    assert conf >= 0.50
    assert is_decoy is False
    assert abs(px - 34.2) < 0.8
    assert abs(py - 28.7) < 0.8
    assert heatmap.shape == (64, 64)


def test_ai_detector_decoy_rejection():
    detector = NanoSpotDetector()
    patch = np.zeros((64, 64), dtype=np.uint8)
    y, x = np.ogrid[:64, :64]
    # Highly elongated decoy flare / booster exhaust streak
    streak = 240.0 * np.exp(-((x - 32.0)**2 / (2 * 1.5**2) + (y - 32.0)**2 / (2 * 12.0**2)))
    patch = np.clip(streak + 10.0, 0, 255).astype(np.uint8)

    detected, px, py, conf, is_decoy, heatmap = detector.detect_spot(
        patch, min_confidence=0.30, enable_decoy_filter=True
    )
    assert is_decoy is True


def test_ai_detector_pure_noise():
    detector = NanoSpotDetector()
    np.random.seed(42)
    patch = np.random.normal(25, 5, (64, 64)).clip(0, 255).astype(np.uint8)

    detected, px, py, conf, is_decoy, heatmap = detector.detect_spot(patch, min_confidence=0.50)
    assert detected is False


def test_beacon_detector_ai_integration():
    cfg = DetectorConfig()
    cfg.algorithm = TrackingAlgorithm.AI_ONNX
    cfg.ai_confidence_threshold = 0.50
    detector = BeaconDetector(cfg)

    frame = np.zeros((480, 640), dtype=np.uint8)
    y, x = np.ogrid[:480, :640]
    # Spot at (320, 240)
    frame += (210.0 * np.exp(-((x - 320.0)**2 + (y - 240.0)**2) / (2 * 3.0**2))).astype(np.uint8)

    res = detector.detect(frame)
    assert res.detected is True
    assert res.algorithm_used == TrackingAlgorithm.AI_ONNX.value
    assert abs(res.x - 320.0) < 1.0
    assert abs(res.y - 240.0) < 1.0
    assert res.heatmap is not None
