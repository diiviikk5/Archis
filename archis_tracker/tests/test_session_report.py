"""Automatic run artifacts preserve evidence needed by evaluators."""
import csv
import json

from archis_tracker.core.config import TrackingState
from archis_tracker.core.telemetry import TelemetryEngine


def test_session_writes_csv_json_and_readable_report(tmp_path):
    telemetry = TelemetryEngine()
    run_dir = telemetry.start_session(tmp_path)
    for frame in range(12):
        telemetry.record_frame(
            t_sim=frame / 30,
            state=TrackingState.TRACKING,
            target_in_fov=True,
            detected=True,
            measured_x=323,
            measured_y=244,
            center_x=320,
            center_y=240,
            pan_deg=0.1,
            tilt_deg=0.2,
            target_speed=40,
            fps=30,
            latency_ms=2,
            snr_db=20,
        )
    assert telemetry.finish_session() == run_dir

    with (run_dir / "telemetry.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    report = json.loads((run_dir / "performance_report.json").read_text(encoding="utf-8"))
    readable = (run_dir / "performance_report.txt").read_text(encoding="utf-8")

    assert len(rows) == 12
    assert rows[0]["Detected"] == "1"
    assert report["metrics"]["total_frames"] == 12
    assert report["metrics"]["average_error_px"] == 5.0
    assert report["metrics"]["max_error_px"] == 5.0
    assert report["metrics"]["lock_retention_pct"] == 100.0
    assert report["metrics"]["camera_update_fps"] == 30.0
    assert report["metrics"]["fps"] == 500.0
    assert "Reacquisition: NOT EVALUATED" in readable
