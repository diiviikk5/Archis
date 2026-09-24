"""
Archis Optical Tracker - Real-time Telemetry & Performance Analyzer
Computes tracking error, acquisition time, re-acquisition time, loss %, FPS, and CSV logging.
"""
import numpy as np
import time
from typing import List, Dict, Any, Optional
from collections import deque
import csv
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from .config import TrackingState, PerformanceThresholds
from archis_tracker import __version__


class TelemetryEngine:
    def __init__(self, thresholds: Optional[PerformanceThresholds] = None, max_history: int = 400):
        self.thresholds = thresholds or PerformanceThresholds()
        self.max_history = max_history
        
        # Performance Counters
        self.total_frames: int = 0
        self.tracked_frames: int = 0
        self.lost_frames: int = 0
        
        # Acquisition Timing
        self.session_start_time = time.time()
        self.acquisition_time_s: float = 0.0
        self.has_first_acquisition: bool = False
        self.consecutive_track_frames: int = 0
        
        # Re-acquisition Timing
        self.loss_start_time: Optional[float] = None
        self.last_reacquisition_time_s: float = 0.0
        self.reacquisition_count: int = 0
        
        # Real-time Metrics
        self.current_error_x: float = 0.0
        self.current_error_y: float = 0.0
        self.current_error_px: float = 0.0
        self.rms_error_px: float = 0.0
        self.target_loss_pct: float = 0.0
        self.current_fps: float = 30.0
        self.pipeline_latency_ms: float = 0.0
        self.simulation_duration_s: float = 0.0
        self.error_sum_px: float = 0.0
        self.max_error_px: float = 0.0
        self.processing_time_sum_ms: float = 0.0
        self.max_processing_time_ms: float = 0.0
        self.processing_times_ms: List[float] = []
        self.current_centroid_error_px: Optional[float] = None
        self.centroid_error_sum_px: float = 0.0
        self.centroid_error_sq_sum_px: float = 0.0
        self.centroid_error_count: int = 0
        self.max_centroid_error_px: float = 0.0
        self.truth_frames: int = 0
        self.loss_event_count: int = 0
        self.reacquisition_times_s: List[float] = []
        
        # Telemetry Rolling History Buffers (for live plotting)
        self.history_time: deque = deque(maxlen=max_history)
        self.history_error: deque = deque(maxlen=max_history)
        self.history_error_x: deque = deque(maxlen=max_history)
        self.history_error_y: deque = deque(maxlen=max_history)
        self.history_centroid_error: deque = deque(maxlen=max_history)
        self.history_pan: deque = deque(maxlen=max_history)
        self.history_tilt: deque = deque(maxlen=max_history)
        self.history_fps: deque = deque(maxlen=max_history)
        self.history_processing_fps: deque = deque(maxlen=max_history)
        self.history_speed: deque = deque(maxlen=max_history)
        
        # Recent squared errors for sliding-window RMS
        self.recent_sq_errors: deque = deque(maxlen=150)
        
        # Logging
        self.is_logging: bool = False
        self.log_file = None
        self.csv_writer = None
        self.session_dir: Optional[Path] = None
        self.session_log_file = None
        self.session_csv_writer = None
        self.session_metadata: Dict[str, Any] = {}

    def reset(self):
        self.total_frames = 0
        self.tracked_frames = 0
        self.lost_frames = 0
        self.session_start_time = time.time()
        self.acquisition_time_s = 0.0
        self.has_first_acquisition = False
        self.consecutive_track_frames = 0
        self.loss_start_time = None
        self.last_reacquisition_time_s = 0.0
        self.reacquisition_count = 0
        self.current_error_x = 0.0
        self.current_error_y = 0.0
        self.current_error_px = 0.0
        self.rms_error_px = 0.0
        self.target_loss_pct = 0.0
        self.current_fps = 30.0
        self.pipeline_latency_ms = 0.0
        self.simulation_duration_s = 0.0
        self.error_sum_px = 0.0
        self.max_error_px = 0.0
        self.processing_time_sum_ms = 0.0
        self.max_processing_time_ms = 0.0
        self.processing_times_ms.clear()
        self.current_centroid_error_px = None
        self.centroid_error_sum_px = 0.0
        self.centroid_error_sq_sum_px = 0.0
        self.centroid_error_count = 0
        self.max_centroid_error_px = 0.0
        self.truth_frames = 0
        self.loss_event_count = 0
        self.reacquisition_times_s.clear()
        self.recent_sq_errors.clear()
        self.history_time.clear()
        self.history_error.clear()
        self.history_error_x.clear()
        self.history_error_y.clear()
        self.history_centroid_error.clear()
        self.history_pan.clear()
        self.history_tilt.clear()
        self.history_fps.clear()
        self.history_processing_fps.clear()
        self.history_speed.clear()

    def record_frame(self, t_sim: float, state: TrackingState,
                     target_in_fov: bool, detected: bool,
                     measured_x: float, measured_y: float,
                     center_x: float, center_y: float,
                     pan_deg: float, tilt_deg: float,
                     target_speed: float, fps: float, latency_ms: float,
                     snr_db: float, truth_x: Optional[float] = None,
                     truth_y: Optional[float] = None,
                     truth_visible: Optional[bool] = None):
        """Records telemetry data point for the current simulation frame."""
        self.total_frames += 1
        self.simulation_duration_s = max(self.simulation_duration_s, t_sim)
        self.current_fps = fps
        self.pipeline_latency_ms = latency_ms
        self.processing_time_sum_ms += latency_ms
        self.max_processing_time_ms = max(self.max_processing_time_ms, latency_ms)
        self.processing_times_ms.append(float(latency_ms))
        self.current_centroid_error_px = None
        
        if detected:
            self.tracked_frames += 1
            self.consecutive_track_frames += 1
            
            # Check Initial Acquisition Time (<= 2.0 s specification)
            if not self.has_first_acquisition and self.consecutive_track_frames >= 10:
                self.acquisition_time_s = t_sim
                self.has_first_acquisition = True
                
            # Check Re-acquisition Time (<= 1.0 s specification)
            if self.loss_start_time is not None:
                reacq_dt = t_sim - self.loss_start_time
                self.last_reacquisition_time_s = reacq_dt
                self.reacquisition_count += 1
                self.reacquisition_times_s.append(reacq_dt)
                self.loss_start_time = None
                
            # Operational pointing error uses sensor-space truth when the
            # simulator/evaluator provides it.  Truth is never passed to the
            # detector, tracker or controller.
            point_x = truth_x if truth_x is not None and truth_visible is not False else measured_x
            point_y = truth_y if truth_y is not None and truth_visible is not False else measured_y
            self.current_error_x = point_x - center_x
            self.current_error_y = point_y - center_y
            self.current_error_px = float(np.hypot(self.current_error_x, self.current_error_y))
            self.recent_sq_errors.append(self.current_error_px ** 2)
            self.error_sum_px += self.current_error_px
            self.max_error_px = max(self.max_error_px, self.current_error_px)
            if truth_x is not None and truth_y is not None and truth_visible is not False:
                self.truth_frames += 1
                self.current_centroid_error_px = float(
                    np.hypot(measured_x - truth_x, measured_y - truth_y)
                )
                self.centroid_error_sum_px += self.current_centroid_error_px
                self.centroid_error_sq_sum_px += self.current_centroid_error_px ** 2
                self.centroid_error_count += 1
                self.max_centroid_error_px = max(
                    self.max_centroid_error_px, self.current_centroid_error_px
                )
            
        else:
            self.lost_frames += 1
            self.consecutive_track_frames = 0
            if self.loss_start_time is None and self.has_first_acquisition:
                self.loss_start_time = t_sim
                self.loss_event_count += 1
                
        # Target Loss Percentage (< 5.0% specification)
        if self.total_frames > 0:
            self.target_loss_pct = (self.lost_frames / self.total_frames) * 100.0
            
        # Sliding-window RMS Tracking Error (<= 10.0 pixels specification)
        if self.recent_sq_errors:
            self.rms_error_px = float(np.sqrt(np.mean(self.recent_sq_errors)))
        else:
            self.rms_error_px = 0.0

        # Append to rolling history
        self.history_time.append(t_sim)
        self.history_error.append(self.current_error_px)
        self.history_error_x.append(self.current_error_x)
        self.history_error_y.append(self.current_error_y)
        self.history_centroid_error.append(
            float("nan") if self.current_centroid_error_px is None else self.current_centroid_error_px
        )
        self.history_pan.append(pan_deg)
        self.history_tilt.append(tilt_deg)
        self.history_fps.append(fps)
        self.history_processing_fps.append(1000.0 / latency_ms if latency_ms > 0 else 0.0)
        self.history_speed.append(target_speed)

        # Log to CSV if active
        row = [
            f"{t_sim:.4f}", state.value, int(target_in_fov), int(detected),
            f"{self.current_error_px:.2f}", f"{self.current_error_x:.2f}",
            f"{self.current_error_y:.2f}", f"{self.rms_error_px:.2f}",
            f"{pan_deg:.3f}", f"{tilt_deg:.3f}", f"{target_speed:.2f}",
            f"{fps:.1f}", f"{latency_ms:.2f}", f"{snr_db:.1f}",
            "" if truth_x is None else f"{truth_x:.3f}",
            "" if truth_y is None else f"{truth_y:.3f}",
            "" if self.current_centroid_error_px is None else f"{self.current_centroid_error_px:.3f}",
        ]
        if self.is_logging and self.csv_writer:
            self.csv_writer.writerow(row)
        if self.session_csv_writer:
            self.session_csv_writer.writerow(row)

    @staticmethod
    def _write_csv_header(writer):
        writer.writerow([
            "Timestamp_s", "State", "Target_In_FOV", "Detected",
            "Tracking_Error_px", "Error_X_px", "Error_Y_px", "RMS_Error_px",
            "Pan_deg", "Tilt_deg", "Target_Speed_px_s", "FPS",
            "Pipeline_Latency_ms", "SNR_dB", "Truth_X_px", "Truth_Y_px",
            "Centroid_Error_px"
        ])

    def start_csv_log(self, filepath: str):
        try:
            self.log_file = open(filepath, "w", newline="", encoding="utf-8")
            self.csv_writer = csv.writer(self.log_file)
            self._write_csv_header(self.csv_writer)
            self.is_logging = True
            return True
        except Exception as e:
            print("Failed to start CSV log:", e)
            return False

    def stop_csv_log(self):
        if self.log_file:
            self.log_file.flush()
            self.log_file.close()
            self.log_file = None
            self.csv_writer = None
        self.is_logging = False

    start_logging = start_csv_log
    stop_logging = stop_csv_log

    def start_session(self, output_root: str | Path, metadata: Optional[Dict[str, Any]] = None) -> Path:
        """Start an automatic, uniquely named run log."""
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.session_dir = Path(output_root) / f"run_{stamp}"
        self.session_dir.mkdir(parents=True, exist_ok=False)
        self.session_log_file = (self.session_dir / "telemetry.csv").open(
            "w", newline="", encoding="utf-8"
        )
        self.session_csv_writer = csv.writer(self.session_log_file)
        self._write_csv_header(self.session_csv_writer)
        self.session_metadata = dict(metadata or {})
        return self.session_dir

    def finish_session(self) -> Optional[Path]:
        """Finalize the automatic CSV and write JSON and text performance reports."""
        if self.session_dir is None:
            return None
        if self.session_log_file:
            self.session_log_file.flush()
            self.session_log_file.close()
        self.session_log_file = None
        self.session_csv_writer = None

        summary = self.get_summary()
        report = {
            "schema_version": 2,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "application": {"name": "Archis Optical Tracker", "version": __version__},
            "session": self.session_metadata,
            "metrics": summary,
            "thresholds": {
                "acquisition_time_s_max": self.thresholds.max_acquisition_time_s,
                "tracking_error_px_max": self.thresholds.max_tracking_error_px,
                "target_loss_pct_max_exclusive": self.thresholds.max_target_loss_pct,
                "reacquisition_time_s_max": self.thresholds.max_reacquisition_time_s,
                "processing_fps_min": self.thresholds.min_processing_fps,
            },
        }
        json_path = self.session_dir / "performance_report.json"
        json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        status = lambda passed: "PASS" if passed else "FAIL"
        lines = [
            "ARCHIS FSOC TRACKING PERFORMANCE REPORT",
            f"Generated (UTC): {report['generated_at_utc']}",
            f"Simulation duration: {summary['simulation_duration_s']:.3f} s",
            f"Frames processed: {summary['total_frames']}",
            f"Average processing time: {summary['average_processing_time_ms']:.3f} ms",
            f"P50 processing time: {summary['processing_p50_ms']:.3f} ms",
            f"P95 processing time: {summary['processing_p95_ms']:.3f} ms",
            f"Maximum processing time: {summary['max_processing_time_ms']:.3f} ms",
            f"Average tracking error: {summary['average_error_px']:.3f} px",
            f"Centroid RMSE: {summary['centroid_rmse_px'] if summary['centroid_rmse_px'] is not None else 'N/A'}",
            f"Maximum tracking error: {summary['max_error_px']:.3f} px",
            f"Lock retention: {summary['lock_retention_pct']:.3f} %",
            f"Loss events: {summary['loss_event_count']}",
            f"Acquisition: {summary['acquisition_time_s']:.3f} s [{status(summary['acquisition_passed'])}]",
            f"RMS pointing error: {summary['rms_error_px']:.3f} px [{status(summary['error_passed'])}]",
            f"Target loss: {summary['target_loss_pct']:.3f} % [{status(summary['loss_passed'])}]",
            f"Mean processing rate: {summary['fps']:.3f} FPS",
            f"Conservative processing rate (1000/p95): {summary['conservative_fps']:.3f} FPS [{status(summary['fps_passed'])}]",
        ]
        if summary["reacquisition_evaluated"]:
            lines.append(
                f"Reacquisition: {summary['reacquisition_time_s']:.3f} s "
                f"[{status(summary['reacquisition_passed'])}]"
            )
        else:
            lines.append("Reacquisition: NOT EVALUATED (no completed loss event)")
        (self.session_dir / "performance_report.txt").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )
        metric_rows = "".join(
            f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>"
            for key, value in summary.items()
        )
        session_rows = "".join(
            f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>"
            for key, value in self.session_metadata.items()
        )
        (self.session_dir / "performance_report.html").write_text(
            "<!doctype html><meta charset='utf-8'><title>Archis Performance Report</title>"
            "<style>body{font:15px system-ui;background:#071018;color:#e7eef5;max-width:960px;margin:40px auto}"
            "table{width:100%;border-collapse:collapse;margin-bottom:28px}th,td{padding:9px;border-bottom:1px solid #294052;text-align:left}"
            "th{color:#83d9ce;width:45%}h1,h2{color:#f2f8fc}</style>"
            f"<h1>Archis FSOC Performance Report</h1><p>Version {html.escape(__version__)}</p>"
            f"<h2>Session</h2><table>{session_rows}</table><h2>Metrics</h2><table>{metric_rows}</table>",
            encoding="utf-8",
        )
        completed_dir = self.session_dir
        self.session_dir = None
        return completed_dir

    def get_summary(self) -> Dict[str, Any]:
        average_error = self.error_sum_px / self.tracked_frames if self.tracked_frames else 0.0
        average_processing = self.processing_time_sum_ms / self.total_frames if self.total_frames else 0.0
        processing_throughput = 1000.0 / average_processing if average_processing > 0 else 0.0
        p50_processing = float(np.percentile(self.processing_times_ms, 50)) if self.processing_times_ms else 0.0
        p95_processing = float(np.percentile(self.processing_times_ms, 95)) if self.processing_times_ms else 0.0
        conservative_throughput = 1000.0 / p95_processing if p95_processing > 0 else 0.0
        lock_retention = self.tracked_frames / self.total_frames * 100.0 if self.total_frames else 0.0
        return {
            "simulation_duration_s": self.simulation_duration_s,
            "total_frames": self.total_frames,
            "tracked_frames": self.tracked_frames,
            "acquisition_time_s": self.acquisition_time_s,
            "acquisition_passed": self.has_first_acquisition and self.acquisition_time_s <= self.thresholds.max_acquisition_time_s,
            "rms_error_px": self.rms_error_px,
            "average_error_px": average_error,
            "max_error_px": self.max_error_px,
            "centroid_mean_px": (
                self.centroid_error_sum_px / self.centroid_error_count
                if self.centroid_error_count else None
            ),
            "centroid_rmse_px": (
                float(np.sqrt(self.centroid_error_sq_sum_px / self.centroid_error_count))
                if self.centroid_error_count else None
            ),
            "centroid_max_px": self.max_centroid_error_px if self.centroid_error_count else None,
            "accuracy_basis": "ground_truth" if self.truth_frames else "observed_tracking",
            "error_passed": self.has_first_acquisition and self.rms_error_px <= self.thresholds.max_tracking_error_px,
            "target_loss_pct": self.target_loss_pct,
            "loss_passed": self.total_frames > 0 and self.target_loss_pct < self.thresholds.max_target_loss_pct,
            "reacquisition_time_s": self.last_reacquisition_time_s,
            "average_reacquisition_time_s": float(np.mean(self.reacquisition_times_s)) if self.reacquisition_times_s else 0.0,
            "loss_event_count": self.loss_event_count,
            "lock_retention_pct": lock_retention,
            "reacquisition_evaluated": self.reacquisition_count > 0,
            "reacquisition_passed": self.reacquisition_count > 0 and self.loss_start_time is None and self.last_reacquisition_time_s <= self.thresholds.max_reacquisition_time_s,
            "fps": processing_throughput,
            "conservative_fps": conservative_throughput,
            "camera_update_fps": self.current_fps,
            "fps_passed": self.total_frames > 0 and conservative_throughput >= self.thresholds.min_processing_fps,
            "average_processing_time_ms": average_processing,
            "processing_p50_ms": p50_processing,
            "processing_p95_ms": p95_processing,
            "max_processing_time_ms": self.max_processing_time_ms,
        }
