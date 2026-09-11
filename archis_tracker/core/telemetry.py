"""
Archis Optical Tracker - Real-time Telemetry & Performance Analyzer
Computes tracking error, acquisition time, re-acquisition time, loss %, FPS, and CSV logging.
"""
import numpy as np
import time
from typing import List, Dict, Any, Optional
from collections import deque
import csv
from .config import TrackingState, PerformanceThresholds


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
        
        # Telemetry Rolling History Buffers (for live plotting)
        self.history_time: deque = deque(maxlen=max_history)
        self.history_error: deque = deque(maxlen=max_history)
        self.history_error_x: deque = deque(maxlen=max_history)
        self.history_error_y: deque = deque(maxlen=max_history)
        self.history_pan: deque = deque(maxlen=max_history)
        self.history_tilt: deque = deque(maxlen=max_history)
        self.history_fps: deque = deque(maxlen=max_history)
        self.history_speed: deque = deque(maxlen=max_history)
        
        # Recent squared errors for sliding-window RMS
        self.recent_sq_errors: deque = deque(maxlen=150)
        
        # Logging
        self.is_logging: bool = False
        self.log_file = None
        self.csv_writer = None

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
        self.recent_sq_errors.clear()
        self.history_time.clear()
        self.history_error.clear()
        self.history_error_x.clear()
        self.history_error_y.clear()
        self.history_pan.clear()
        self.history_tilt.clear()
        self.history_fps.clear()
        self.history_speed.clear()

    def record_frame(self, t_sim: float, state: TrackingState,
                     target_in_fov: bool, detected: bool,
                     measured_x: float, measured_y: float,
                     center_x: float, center_y: float,
                     pan_deg: float, tilt_deg: float,
                     target_speed: float, fps: float, latency_ms: float,
                     snr_db: float):
        """Records telemetry data point for the current simulation frame."""
        self.total_frames += 1
        self.current_fps = fps
        self.pipeline_latency_ms = latency_ms
        
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
                self.loss_start_time = None
                
            # Error from optical boresight center (320, 240)
            self.current_error_x = measured_x - center_x
            self.current_error_y = measured_y - center_y
            self.current_error_px = float(np.hypot(self.current_error_x, self.current_error_y))
            self.recent_sq_errors.append(self.current_error_px ** 2)
            
        else:
            self.lost_frames += 1
            self.consecutive_track_frames = 0
            if self.loss_start_time is None and self.has_first_acquisition:
                self.loss_start_time = t_sim
                
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
        self.history_pan.append(pan_deg)
        self.history_tilt.append(tilt_deg)
        self.history_fps.append(fps)
        self.history_speed.append(target_speed)

        # Log to CSV if active
        if self.is_logging and self.csv_writer:
            self.csv_writer.writerow([
                f"{t_sim:.4f}", state.value, f"{self.current_error_px:.2f}",
                f"{self.current_error_x:.2f}", f"{self.current_error_y:.2f}",
                f"{self.rms_error_px:.2f}", f"{pan_deg:.3f}", f"{tilt_deg:.3f}",
                f"{target_speed:.2f}", f"{fps:.1f}", f"{latency_ms:.2f}", f"{snr_db:.1f}"
            ])

    def start_csv_log(self, filepath: str):
        try:
            self.log_file = open(filepath, "w", newline="", encoding="utf-8")
            self.csv_writer = csv.writer(self.log_file)
            self.csv_writer.writerow([
                "Timestamp_s", "State", "Tracking_Error_px", "Error_X_px", "Error_Y_px",
                "RMS_Error_px", "Pan_deg", "Tilt_deg", "Target_Speed_px_s",
                "FPS", "Pipeline_Latency_ms", "SNR_dB"
            ])
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

    def get_summary(self) -> Dict[str, Any]:
        return {
            "acquisition_time_s": self.acquisition_time_s,
            "acquisition_passed": self.has_first_acquisition and self.acquisition_time_s <= self.thresholds.max_acquisition_time_s,
            "rms_error_px": self.rms_error_px,
            "error_passed": self.has_first_acquisition and self.rms_error_px <= self.thresholds.max_tracking_error_px,
            "target_loss_pct": self.target_loss_pct,
            "loss_passed": self.total_frames > 0 and self.target_loss_pct < self.thresholds.max_target_loss_pct,
            "reacquisition_time_s": self.last_reacquisition_time_s,
            "reacquisition_passed": self.has_first_acquisition and self.loss_start_time is None and self.last_reacquisition_time_s <= self.thresholds.max_reacquisition_time_s,
            "fps": self.current_fps,
            "fps_passed": self.total_frames > 0 and self.current_fps >= self.thresholds.min_processing_fps
        }
