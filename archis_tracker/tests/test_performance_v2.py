from __future__ import annotations

import json

import numpy as np

from archis_tracker.core.config import DetectorConfig, TrackingAlgorithm
from archis_tracker.core.contracts import GroundTruthSample
from archis_tracker.core.performance import PerformanceRecorder
from archis_tracker.core.tracker import TrackingSystem


def test_performance_report_uses_truth_and_exports_three_formats(tmp_path):
    tracker = TrackingSystem(det_config=DetectorConfig(algorithm=TrackingAlgorithm.IWC))
    recorder = PerformanceRecorder("truth run", (640, 480))
    yy, xx = np.ogrid[:480, :640]
    image = (220 * np.exp(-((xx-320)**2 + (yy-240)**2)/(2*3**2))).astype(np.uint8)
    for _ in range(8):
        tracker.step_external_frame(image, 1/30, GroundTruthSample(320, 240))
        recorder.record(tracker.last_result, tracker.last_truth, 30)
    summary = recorder.summary()
    assert summary.accuracy_basis == "ground_truth"
    assert summary.centroid_rmse_px is not None and summary.centroid_rmse_px < 1
    paths = recorder.export(tmp_path)
    assert set(paths) == {"csv", "json", "html"}
    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert payload["schema_version"] == 2
    assert payload["summary"]["accuracy_basis"] == "ground_truth"
    rendered = paths["html"].read_text(encoding="utf-8")
    assert "Configured thresholds" in rendered
    assert "AI model provenance" in rendered
    assert "Scenario configuration" in rendered


def test_truth_free_recording_does_not_claim_accuracy():
    tracker = TrackingSystem(det_config=DetectorConfig(algorithm=TrackingAlgorithm.IWC))
    recorder = PerformanceRecorder("observed", (640, 480))
    image = np.zeros((480, 640), dtype=np.uint8); image[235:245, 315:325] = 255
    for _ in range(4):
        tracker.step_external_frame(image, 1/30)
        recorder.record(tracker.last_result, None, 30)
    summary = recorder.summary()
    assert summary.accuracy_basis == "observed_tracking"
    assert summary.centroid_rmse_px is None


def test_invisible_truth_is_logged_but_not_claimed_as_accuracy():
    tracker = TrackingSystem(det_config=DetectorConfig(algorithm=TrackingAlgorithm.IWC))
    recorder = PerformanceRecorder("invisible", (640, 480))
    image = np.zeros((480, 640), dtype=np.uint8)
    for _ in range(4):
        truth = GroundTruthSample(320, 240, visible=False)
        tracker.step_external_frame(image, 1/30, truth)
        recorder.record(tracker.last_result, truth, 30)
    summary = recorder.summary()
    assert summary.accuracy_basis == "observed_tracking"
    assert summary.centroid_rmse_px is None


def test_expected_dropout_requires_a_measured_reacquisition():
    tracker = TrackingSystem(det_config=DetectorConfig(algorithm=TrackingAlgorithm.IWC))
    recorder = PerformanceRecorder(
        "dropout expected", (640, 480),
        configuration={"disturbances": {"dropout": {"enabled": True, "start_s": 0.1, "duration_s": 0.1}}},
    )
    image = np.zeros((480, 640), dtype=np.uint8); image[235:245, 315:325] = 255
    for _ in range(12):
        tracker.step_external_frame(image, 1/30, GroundTruthSample(320, 240))
        recorder.record(tracker.last_result, tracker.last_truth, 30)
    assert recorder.summary().reacquisition_passed is False


def test_identical_seed_runs_have_identical_report_fingerprint():
    fingerprints = []
    for _ in range(2):
        tracker = TrackingSystem(det_config=DetectorConfig(algorithm=TrackingAlgorithm.IWC))
        recorder = PerformanceRecorder("repeatable", (640, 480))
        for _ in range(8):
            tracker.step(1/30)
            recorder.record(tracker.last_result, tracker.last_truth, 30)
        fingerprints.append(recorder.summary().run_fingerprint)
    assert fingerprints[0] == fingerprints[1]
