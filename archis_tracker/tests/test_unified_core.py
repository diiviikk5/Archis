"""Integration coverage for the Qlyraxis-derived Archis production core."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import json

import cv2
import numpy as np
import pytest

from archis_tracker.core.codelock import CodeLock
from archis_tracker.core.config import DetectorConfig, TrackingAlgorithm
from archis_tracker.core.contracts import (
    CanonicalTrackingState, Detection, FramePacket, GroundTruthSample,
)
from archis_tracker.core.scenario import Scenario, ScenarioError, load_scenario, tracker_from_scenario, validate_scenario
from archis_tracker.core.state_machine import TrackingStateMachine
from archis_tracker.core.tracker import TrackingSystem
from archis_tracker.core.truth import TruthSidecar, TruthSidecarError


def _spot(width: int, height: int, x: float, y: float) -> np.ndarray:
    yy, xx = np.ogrid[:height, :width]
    return np.clip(12 + 230 * np.exp(-((xx-x)**2 + (yy-y)**2)/(2*2.7**2)), 0, 255).astype(np.uint8)


@pytest.mark.parametrize("xy", [(35, 35), (600, 35), (35, 440), (600, 440)])
def test_initial_acquisition_is_full_frame(xy):
    tracker = TrackingSystem(det_config=DetectorConfig(algorithm=TrackingAlgorithm.HYBRID))
    detection = tracker.step_external_frame(_spot(640, 480, *xy), 1 / 30)
    assert detection.detected
    assert np.hypot(detection.x - xy[0], detection.y - xy[1]) < 1.5
    assert tracker.last_result.diagnostics["search_scope"] == "full"


def test_contracts_are_immutable_and_truth_is_separate():
    image = np.zeros((4, 4), dtype=np.uint8)
    packet = FramePacket(0, 0.0, image, metadata={"source": "test"})
    truth = GroundTruthSample(1.0, 2.0)
    assert not hasattr(packet, "truth")
    with pytest.raises(FrozenInstanceError):
        truth.x_px = 3.0  # type: ignore[misc]
    with pytest.raises(ValueError):
        image[0, 0] = 1
    with pytest.raises(TypeError):
        packet.metadata["source"] = "changed"  # type: ignore[index]


def test_explicit_state_machine_coasts_and_reacquires():
    machine = TrackingStateMachine()
    assert machine.update(True, 1/30) == CanonicalTrackingState.ACQUIRE
    assert machine.update(True, 1/30) == CanonicalTrackingState.ACQUIRE
    assert machine.update(True, 1/30) == CanonicalTrackingState.TRACK
    assert machine.update(False, 1/30) == CanonicalTrackingState.COAST
    for _ in range(13):
        state = machine.update(False, 1/30)
    assert state == CanonicalTrackingState.REACQUIRE
    assert machine.use_prediction_gate
    for _ in range(19):
        machine.update(False, 1/30)
    assert not machine.use_prediction_gate
    assert machine.update(True, 1/30) == CanonicalTrackingState.ACQUIRE


def test_seeded_simulation_is_reproducible():
    first, second = TrackingSystem(), TrackingSystem()
    first.disturb_config.enable_gaussian_noise = second.disturb_config.enable_gaussian_noise = True
    for _ in range(4):
        first.step(1/30); second.step(1/30)
        assert np.array_equal(first.current_frame, second.current_frame)
        assert first.last_truth == second.last_truth


def test_configured_seed_rebuilds_all_random_sources():
    first, second = TrackingSystem(), TrackingSystem()
    for tracker in (first, second):
        tracker.configure_random_seed(777)
        tracker.disturb_config.enable_gaussian_noise = True
        tracker.reset()
        tracker.step(1/30)
    assert np.array_equal(first.current_frame, second.current_frame)
    third = TrackingSystem()
    third.configure_random_seed(778)
    third.disturb_config.enable_gaussian_noise = True
    third.reset(); third.step(1/30)
    assert not np.array_equal(first.current_frame, third.current_frame)


def test_truth_sidecars_support_csv_json_and_opt_in_interpolation(tmp_path):
    csv_path = tmp_path / "truth.csv"
    csv_path.write_text("frame_index,timestamp_s,x_px,y_px,visible,target_id\n0,0,10,20,true,A\n2,0.2,30,40,true,A\n", encoding="utf-8")
    sidecar = TruthSidecar.load(csv_path)
    assert sidecar.sample_for(0, 0).x_px == 10
    assert sidecar.sample_for(1, 0.1) is None
    assert sidecar.sample_for(1, 0.1, interpolate=True).x_px == pytest.approx(20)

    json_path = tmp_path / "truth.json"
    json_path.write_text(json.dumps({"frames": [{"frame_index": 4, "x_px": 5, "y_px": 6, "visible": False}]}), encoding="utf-8")
    assert TruthSidecar.load(json_path).sample_for(4, 0).visible is False
    with pytest.raises(TruthSidecarError):
        TruthSidecar.load(tmp_path / "missing.csv")

    duplicate = tmp_path / "duplicate.csv"
    duplicate.write_text("frame_index,x_px,y_px\n1,2,3\n1,4,5\n", encoding="utf-8")
    with pytest.raises(TruthSidecarError):
        TruthSidecar.load(duplicate)

    malformed = tmp_path / "malformed.json"
    malformed.write_text(json.dumps([{"timestamp_s": 0, "x_px": 1, "y_px": 2, "visible": "perhaps"}]))
    with pytest.raises(TruthSidecarError):
        TruthSidecar.load(malformed)


def test_legacy_preset_migrates_to_schema_v2():
    scenario = load_scenario("archis_tracker/presets/nominal_leo.json")
    assert scenario.data["schema_version"] == 2
    assert scenario.seed == 26169
    tracker = tracker_from_scenario(scenario)
    assert tracker.detector.config.algorithm == TrackingAlgorithm.HYBRID


def test_scenario_validation_rejects_bad_seed(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
    with pytest.raises(ScenarioError):
        load_scenario(path)


def test_codelock_rejects_constant_light_and_accepts_pattern():
    detector = CodeLock("1011001", minimum_correlation=0.7)
    candidate = Detection(32, 32, 0.9, 8, 8)
    accepted = ()
    for index, bit in enumerate("1011001" * 2):
        image = np.full((64, 64), 8, dtype=np.uint8)
        cv2.circle(image, (32, 32), 4, 240 if bit == "1" else 70, -1)
        accepted = detector.filter(image, (candidate,), index)
    assert accepted and accepted[0].identity_score >= 0.7

    constant = CodeLock("1011001", minimum_correlation=0.7)
    for index in range(14):
        image = np.full((64, 64), 8, dtype=np.uint8)
        cv2.circle(image, (32, 32), 4, 240, -1)
        rejected = constant.filter(image, (candidate,), index)
    assert rejected == ()


def test_native_external_truth_populates_centroid_metrics():
    tracker = TrackingSystem()
    truth = GroundTruthSample(480, 360)
    tracker.step_external_frame(_spot(960, 720, 480, 360), 1/30, truth)
    assert tracker.current_frame.shape == (720, 960)
    assert tracker.telemetry.truth_frames == 0  # not TRACK until temporal confirmation
    tracker.step_external_frame(_spot(960, 720, 480, 360), 1/30, truth)
    tracker.step_external_frame(_spot(960, 720, 480, 360), 1/30, truth)
    assert tracker.telemetry.truth_frames == 1
    assert tracker.telemetry.current_centroid_error_px < 1


def test_native_external_theoretical_command_uses_native_sensor_center():
    tracker = TrackingSystem(det_config=DetectorConfig(algorithm=TrackingAlgorithm.IWC))
    centered = _spot(960, 720, 480, 360)
    for _ in range(3):
        tracker.step_external_frame(centered, 1/30)
    assert tracker.last_result.command is not None
    assert abs(tracker.last_result.command.pan_rate_deg_s) < 0.2
    assert abs(tracker.last_result.command.tilt_rate_deg_s) < 0.2


def test_schema_v2_can_create_primary_and_decoy_targets():
    raw = json.loads(open("scenarios/schema_v2_example.json", encoding="utf-8").read())
    primary = dict(raw["target"])
    primary["initial_location"] = "top_left"
    decoy = dict(raw["target"])
    decoy["initial_position_px"] = [1100, 1000]
    raw["targets"] = [primary, decoy]
    scenario = Scenario(validate_scenario(raw))
    tracker = tracker_from_scenario(scenario)
    assert tracker.primary_target.x < 1000 and tracker.primary_target.y < 1000
    assert len(tracker.secondary_targets) == 1


def test_codelock_rejects_invalid_runtime_configuration():
    with pytest.raises(ValueError):
        CodeLock("1011001", symbol_frames=0)
    with pytest.raises(ValueError):
        CodeLock("1011001", minimum_correlation=1.1)
