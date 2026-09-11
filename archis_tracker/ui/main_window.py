"""
Archis Optical Tracker - Master Application Window
Integrates Viewport, Minimap, Telemetry Dashboard, PyQTGraph Charts, and Control Panel.
"""
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QSplitter, QStatusBar, QToolBar, QLabel, QMessageBox)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QIcon, QAction
import sys
import time

from ..core.tracker import TrackingSystem
from .style import DARK_THEME_QSS
from .viewport import ViewportWidget
from .minimap import MinimapWidget
from .telemetry_display import TelemetryDashboard
from .charts import TelemetryChartsWidget
from .control_panel import ControlPanelWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Archis FSOC Optical Tracker // Autonomous Camera Tracking System")
        self.resize(1340, 880)
        self.setStyleSheet(DARK_THEME_QSS)
        
        # 1. Initialize Tracking Engine
        self.tracker = TrackingSystem()
        
        # 2. Build UI Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(10)
        
        # Left/Center Splitter (Displays & Charts)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        
        # Top Metrics Bar
        self.telemetry_bar = TelemetryDashboard(self.tracker.telemetry.thresholds)
        left_layout.addWidget(self.telemetry_bar)
        
        # Center Video & Minimap Row
        center_row = QHBoxLayout()
        center_row.setSpacing(8)
        
        self.viewport = ViewportWidget()
        center_row.addWidget(self.viewport, stretch=3)
        
        self.minimap = MinimapWidget()
        self.minimap.set_references(self.tracker.primary_target, self.tracker.camera, self.tracker.secondary_targets)
        center_row.addWidget(self.minimap, stretch=1)
        
        left_layout.addLayout(center_row, stretch=3)
        
        # Bottom Telemetry Strip Charts
        self.charts = TelemetryChartsWidget()
        left_layout.addWidget(self.charts, stretch=2)
        
        root_layout.addWidget(left_widget, stretch=4)
        
        # Right Control Panel
        self.control_panel = ControlPanelWidget(self.tracker)
        root_layout.addWidget(self.control_panel, stretch=1)
        
        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("SYSTEM READY • 640x480 MONOCHROME FPA • 2000x2000 VIRTUAL ENVIRONMENT")
        
        # Simulation Loop Timer (Targeting 30-60 Hz)
        self.sim_timer = QTimer(self)
        self.sim_timer.timeout.connect(self._simulation_tick)
        self.last_tick_time = time.perf_counter()
        self.sim_timer.start(int(1000.0 / self.tracker.cam_config.update_rate_hz))

    def _simulation_tick(self):
        """Executes one real-time tracking cycle and updates UI widgets."""
        now = time.perf_counter()
        dt = max(0.005, min(0.1, now - self.last_tick_time))
        self.last_tick_time = now
        
        # Execute Tracking System cycle
        det = self.tracker.step(dt)
        
        # 1. Update Camera Viewport
        self.viewport.update_frame(
            frame_np=self.tracker.current_frame,
            detection=det,
            pred_x=self.tracker.latest_pred_x,
            pred_y=self.tracker.latest_pred_y,
            state=self.tracker.state,
            pan_deg=self.tracker.camera.pan_deg,
            tilt_deg=self.tracker.camera.tilt_deg,
            fps=self.tracker.telemetry.current_fps,
            latency_ms=self.tracker.telemetry.pipeline_latency_ms,
            error_px=self.tracker.telemetry.current_error_px,
            rms_error_px=self.tracker.telemetry.rms_error_px
        )
        
        # 2. Update Global Minimap
        self.minimap.update()
        
        # 3. Update Numerical Metrics Card Dashboard
        t = self.tracker.telemetry
        self.telemetry_bar.update_metrics(
            current_error=t.current_error_px,
            rms_error=t.rms_error_px,
            acq_time=t.acquisition_time_s,
            has_acq=t.has_first_acquisition,
            loss_pct=t.target_loss_pct,
            reacq_time=t.last_reacquisition_time_s,
            fps=t.current_fps,
            state=self.tracker.state
        )
        
        # 4. Update PyQTGraph Telemetry Charts
        self.charts.update_data(
            times=t.history_time,
            errors=t.history_error,
            pans=t.history_pan,
            tilts=t.history_tilt,
            fps_list=t.history_fps,
            speeds=t.history_speed
        )
