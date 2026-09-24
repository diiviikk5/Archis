"""Unit tests for TelemetryEngine performance specifications."""
import pytest
from archis_tracker.core.telemetry import TelemetryEngine
from archis_tracker.core.config import TrackingState


def test_empty_session_cannot_pass_benchmark():
    summary = TelemetryEngine().get_summary()
    for criterion in ("acquisition", "error", "loss", "reacquisition", "fps"):
        assert not summary[f"{criterion}_passed"]
    assert not summary["reacquisition_evaluated"]


def test_unresolved_loss_and_exact_loss_limit_fail():
    telem = TelemetryEngine()
    telem.has_first_acquisition = True
    telem.total_frames = 20
    telem.target_loss_pct = 5.0
    telem.loss_start_time = 1.0
    summary = telem.get_summary()
    assert not summary["loss_passed"]
    assert not summary["reacquisition_passed"]


def test_completed_reacquisition_is_measured():
    telem = TelemetryEngine()
    telem.has_first_acquisition = True
    telem.reacquisition_count = 1
    telem.last_reacquisition_time_s = 0.4
    telem.total_frames = 100
    telem.current_fps = 30.0
    summary = telem.get_summary()
    assert summary["reacquisition_evaluated"]
    assert summary["reacquisition_passed"]


def test_telemetry_metrics_tracking():
    telem = TelemetryEngine()
    dt = 1.0 / 30.0
    
    # Feed 60 frames with error = 4.0 px (well within 10px specification)
    for i in range(60):
        t_sim = i * dt
        telem.record_frame(
            t_sim=t_sim, state=TrackingState.TRACKING, target_in_fov=True, detected=True,
            measured_x=324.0, measured_y=240.0, center_x=320.0, center_y=240.0,
            pan_deg=0.1, tilt_deg=0.0, target_speed=40.0, fps=30.0, latency_ms=2.0, snr_db=25.0
        )
        
    summary = telem.get_summary()
    assert summary["acquisition_passed"], "Acquisition time must pass <= 2.0s"
    assert summary["error_passed"], "Tracking error must pass <= 10.0px"
    assert summary["loss_passed"], "Target loss must pass < 5%"
    assert summary["fps_passed"], "FPS must pass >= 20"


def test_session_latency_uses_p95_for_conservative_throughput():
    telem = TelemetryEngine()
    for index, latency in enumerate((1.0, 2.0, 3.0, 4.0, 100.0)):
        telem.record_frame(
            t_sim=index / 30, state=TrackingState.TRACKING,
            target_in_fov=True, detected=True,
            measured_x=320, measured_y=240, center_x=320, center_y=240,
            pan_deg=0, tilt_deg=0, target_speed=0, fps=30,
            latency_ms=latency, snr_db=20,
        )
    summary = telem.get_summary()
    assert summary["processing_p50_ms"] == 3.0
    assert summary["processing_p95_ms"] == pytest.approx(80.8)
    assert summary["max_processing_time_ms"] == 100.0
    assert summary["conservative_fps"] == pytest.approx(1000 / 80.8)
    assert not summary["fps_passed"]
