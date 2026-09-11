"""Unit tests for TelemetryEngine performance specifications."""
import pytest
from archis_tracker.core.telemetry import TelemetryEngine
from archis_tracker.core.config import TrackingState


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
