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
    assert res.heatmap_bbox == (288, 208, 64, 64)


def test_missing_model_does_not_masquerade_as_ai(tmp_path):
    detector = BeaconDetector(DetectorConfig(algorithm=TrackingAlgorithm.AI_ONNX))
    detector.ai_detector = NanoSpotDetector(str(tmp_path / 'missing.onnx'))
    result = detector.detect(np.full((480, 640), 200, dtype=np.uint8))
    assert not result.detected
    assert result.algorithm_used == 'ONNX unavailable'
    assert result.heatmap is None


def test_corrupt_model_is_reported(tmp_path):
    path = tmp_path / 'broken.onnx'
    path.write_bytes(b'not an ONNX graph')
    detector = NanoSpotDetector(str(path))
    assert not detector.is_loaded
    assert detector.status == 'Model load failed'


@pytest.mark.parametrize('xy', [(12.3, 19.7), (31.1, 45.2), (51.6, 10.4)])
def test_real_inference_tracks_input_not_fixed_coordinates(xy):
    detector = NanoSpotDetector()
    y, x = np.ogrid[:64, :64]
    patch = (15 + 220 * np.exp(-((x-xy[0])**2+(y-xy[1])**2)/(2*2.5**2))).astype(np.uint8)
    result = detector.detect_spot(patch)
    assert result[0]
    assert np.hypot(result[1]-xy[0], result[2]-xy[1]) < 1
    assert np.ptp(result[5]) > 0.2
    assert not detector.detect_spot(np.zeros_like(patch))[0]


def test_model_provenance_matches_bundled_weights():
    detector = NanoSpotDetector()
    assert detector.status == 'synthetic-trained CNN / CPU'


def test_threshold_and_shape_filter_affect_real_inference():
    detector = NanoSpotDetector()
    y, x = np.ogrid[:64, :64]
    streak = (10 + 240 * np.exp(-((x-32)**2/(2*1.5**2)+(y-32)**2/(2*12**2)))).astype(np.uint8)
    assert detector.detect_spot(streak, min_confidence=0.3, enable_decoy_filter=False)[0]
    assert not detector.detect_spot(streak, min_confidence=0.3, enable_decoy_filter=True)[0]
    assert not detector.detect_spot(streak, min_confidence=1.0, enable_decoy_filter=False)[0]


def test_inference_failure_is_explicit():
    import cv2
    detector = BeaconDetector(DetectorConfig(algorithm=TrackingAlgorithm.AI_ONNX))
    # Fault injection only; successful-inference tests use the actual bundled graph.
    class FailedNet:
        def setInput(self, blob):
            raise cv2.error('injected runtime failure')
    detector.ai_detector.net = FailedNet()
    result = detector.detect(np.zeros((480, 640), dtype=np.uint8))
    assert not result.detected
    assert result.algorithm_used == 'ONNX inference failed'
    assert detector.ai_detector.status == 'Inference failed'


def test_ai_gate_heatmap_uses_sensor_coordinates():
    detector = BeaconDetector(DetectorConfig(algorithm=TrackingAlgorithm.AI_ONNX))
    y, x = np.ogrid[:480, :640]
    frame = (15 + 220*np.exp(-((x-200)**2+(y-170)**2)/(2*2.5**2))).astype(np.uint8)
    result = detector.detect(frame, predicted_pos=(200, 170))
    assert result.detected
    hx, hy, hw, hh = result.heatmap_bbox
    assert hx <= result.x < hx + hw
    assert hy <= result.y < hy + hh
    assert abs(result.x-200) < 1
    assert abs(result.y-170) < 1
