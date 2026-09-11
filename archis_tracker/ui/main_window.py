"""Primary desktop operator workspace for Archis optical tracking."""
from __future__ import annotations

import os
import time

from PyQt6.QtCore import QSettings, QStandardPaths, Qt, QTimer, QUrl
from PyQt6.QtGui import QAction, QDesktopServices
from PyQt6.QtWidgets import (
    QFrame, QFileDialog, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QSizePolicy, QSplitter, QStatusBar, QVBoxLayout, QWidget,
)

from ..core.config import TrackingState
from ..core.presets import PresetError
from ..core.tracker import TrackingSystem
from ..core.video_source import VideoSource, VideoSourceError
from .charts import TelemetryChartsWidget
from .control_panel import ControlPanelWidget
from .minimap import MinimapWidget
from .onboarding import OnboardingDialog
from .style import DARK_THEME_QSS
from .telemetry_display import TelemetryDashboard
from .viewport import ViewportWidget
from .workspaces import DesktopWorkspaces


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Archis Optical Tracking Console")
        self.resize(1480, 920)
        self.setMinimumSize(1120, 720)
        self.setStyleSheet(DARK_THEME_QSS)
        self.settings = QSettings("Archis", "OpticalTracker")
        self.tracker = TrackingSystem()
        self.is_running = False
        self.video_source = None

        reports_root = os.path.join(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation),
            "Archis Tracker", "Reports",
        )
        self.session_dir = self.tracker.telemetry.start_session(reports_root)
        self._build_workspace()
        self._build_shortcuts()

        self.sim_timer = QTimer(self)
        self.sim_timer.timeout.connect(self._simulation_tick)
        self.last_tick_time = time.perf_counter()
        self.sim_timer.start(round(1000.0 / self.tracker.cam_config.update_rate_hz))
        self._update_run_state()
        if not self.settings.value("onboarding_complete", False, type=bool):
            QTimer.singleShot(250, self._show_onboarding)

    def _build_workspace(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())
        self.phase_strip = self._build_phase_strip()
        self.phase_strip.setParent(self)
        self.phase_strip.hide()

        workspace = QSplitter(Qt.Orientation.Horizontal)
        workspace.setObjectName("workspaceSplitter")
        workspace.setChildrenCollapsible(False)
        self.control_panel = ControlPanelWidget(self.tracker)
        self.control_panel.setObjectName("missionPanel")
        self.control_panel.setMinimumWidth(290)
        self.control_panel.setMaximumWidth(370)
        self.control_panel.preset_selected_signal.connect(self._load_preset)
        self.control_panel.start_log_signal.connect(self._start_csv_logging)
        self.control_panel.stop_log_signal.connect(self._stop_csv_logging)
        self.control_panel.setParent(self)
        self.control_panel.hide()

        center = QWidget()
        center.setObjectName("centerWorkspace")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(14, 12, 14, 12)
        center_layout.setSpacing(10)
        self.telemetry_bar = TelemetryDashboard(self.tracker.telemetry.thresholds)
        center_layout.addWidget(self.telemetry_bar)

        optical_row = QSplitter(Qt.Orientation.Horizontal)
        optical_row.setObjectName("opticalSplitter")
        optical_row.setChildrenCollapsible(False)
        self.viewport = ViewportWidget()
        self.viewport.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.viewport.designate_target_signal.connect(self._on_viewport_designated)
        self.viewport.spawn_decoy_signal.connect(self._on_viewport_spawn_decoy)
        optical_row.addWidget(self.viewport)
        self.minimap = MinimapWidget()
        self.minimap.setMinimumWidth(220)
        self.minimap.setMaximumWidth(310)
        self.minimap.set_references(self.tracker.primary_target, self.tracker.camera, self.tracker.secondary_targets)
        self.minimap.designate_world_signal.connect(self._on_minimap_designated)
        self.minimap.spawn_decoy_world_signal.connect(self._on_minimap_spawn_decoy)
        optical_row.addWidget(self.minimap)
        optical_row.setStretchFactor(0, 5)
        optical_row.setStretchFactor(1, 2)
        center_layout.addWidget(optical_row, 5)
        self.charts = TelemetryChartsWidget()
        center_layout.addWidget(self.charts, 2)
        self.desktop = DesktopWorkspaces(self, center)
        root.addWidget(self.desktop, 1)

        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Choose a scenario, then start acquisition.")

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("appHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(10)
        mark = QLabel("A")
        mark.setObjectName("brandMark")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setFixedSize(38, 38)
        brand = QVBoxLayout()
        brand.setSpacing(0)
        title = QLabel("ARCHIS")
        title.setObjectName("brandTitle")
        subtitle = QLabel("OPTICAL TRACKING CONSOLE")
        subtitle.setObjectName("brandSubtitle")
        brand.addWidget(title)
        brand.addWidget(subtitle)
        layout.addWidget(mark)
        layout.addLayout(brand)
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setObjectName("headerDivider")
        layout.addWidget(divider)
        terminal = QLabel("Optical Tracking")
        terminal.setObjectName("terminalLabel")
        layout.addWidget(terminal)
        layout.addStretch()
        self.engine_badge = QLabel("ENGINE READY")
        self.engine_badge.setObjectName("engineBadge")
        layout.addWidget(self.engine_badge)
        self.source_button = QPushButton("Open MP4")
        self.source_button.setObjectName("secondaryButton")
        self.source_button.clicked.connect(self._open_video)
        layout.addWidget(self.source_button)
        for text, callback in ():
            button = QPushButton(text)
            button.setObjectName("secondaryButton")
            button.clicked.connect(callback)
            layout.addWidget(button)
        self.reset_button = QPushButton("Reset")
        self.reset_button.setObjectName("secondaryButton")
        self.reset_button.clicked.connect(self._reset_run)
        layout.addWidget(self.reset_button)
        self.run_button = QPushButton("Start run")
        self.run_button.setObjectName("primaryButton")
        self.run_button.clicked.connect(self._toggle_run)
        layout.addWidget(self.run_button)
        return header

    def _build_phase_strip(self) -> QWidget:
        strip = QFrame()
        strip.setObjectName("phaseStrip")
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(0)
        self.phase_labels = []
        for index, text in enumerate(("1  CONFIGURE", "2  ACQUIRE", "3  TRACK", "4  REVIEW")):
            label = QLabel(text)
            label.setObjectName("phaseActive" if index == 0 else "phaseIdle")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label, 1)
            self.phase_labels.append(label)
        return strip

    def _build_shortcuts(self):
        for shortcut, callback in (("Space", self._toggle_run), ("Ctrl+R", self._reset_run)):
            action = QAction(self)
            action.setShortcut(shortcut)
            action.triggered.connect(callback)
            self.addAction(action)

    def _show_onboarding(self):
        dialog = OnboardingDialog(self)
        if dialog.exec():
            self.settings.setValue("onboarding_complete", True)
            if dialog.start_nominal:
                self._load_preset("nominal_leo.json")
                self._set_running(True)

    def _toggle_run(self):
        self._set_running(not self.is_running)

    def _set_running(self, running: bool):
        if running and self.tracker.telemetry.session_dir is None:
            self.tracker.telemetry.reset()
            self.session_dir = self.tracker.telemetry.start_session(self.session_dir.parent)
        self.is_running = running
        if running:
            self.desktop.navigate(2)
        self.last_tick_time = time.perf_counter()
        self._update_run_state()
        message = "Acquisition and tracking are running." if running else "Run paused. Configuration remains editable."
        self.status_bar.showMessage(message)

    def _update_run_state(self):
        self.run_button.setText("Pause run" if self.is_running else "Start run")
        self.run_button.setProperty("running", self.is_running)
        self.run_button.style().unpolish(self.run_button)
        self.run_button.style().polish(self.run_button)
        self.engine_badge.setText("ENGINE RUNNING" if self.is_running else "ENGINE READY")
        self.phase_labels[1].setObjectName("phaseActive" if self.is_running else "phaseIdle")
        for label in self.phase_labels:
            label.style().unpolish(label)
            label.style().polish(label)

    def _reset_run(self):
        self._set_running(False)
        self.tracker.telemetry.finish_session()
        self.tracker.reset()
        self.session_dir = self.tracker.telemetry.start_session(self.session_dir.parent)
        if self.video_source:
            self.video_source.rewind()
        self.charts.clear_data()
        self.status_bar.showMessage("Run reset. Scenario configuration was preserved.")

    def _open_reports(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.session_dir)))

    def _open_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open evaluator video", "", "Video files (*.mp4 *.avi *.mov *.mkv)"
        )
        if not path:
            return
        try:
            source = VideoSource(path)
        except VideoSourceError as exc:
            QMessageBox.warning(self, "Video could not be opened", str(exc))
            return
        if self.video_source:
            self.video_source.close()
        self.video_source = source
        self._set_running(False)
        self.tracker.telemetry.finish_session()
        self.tracker.reset()
        self.session_dir = self.tracker.telemetry.start_session(self.session_dir.parent)
        self.minimap.hide()
        self.desktop.navigate(2)
        self.sim_timer.setInterval(max(1, round(1000.0 / source.fps)))
        self.source_button.setText("Video: " + source.path.name[:20])
        self.status_bar.showMessage(
            f"Video input ready: {source.width}x{source.height} at {source.fps:.2f} FPS. Press Start run."
        )

    def _on_viewport_designated(self, vx: float, vy: float):
        wx, wy = self.tracker.camera.viewport_to_world(vx, vy)
        self.tracker.designate_target_at(wx, wy)
        self.status_bar.showMessage(f"Target designated at {wx:.0f}, {wy:.0f}.", 3000)

    def _on_viewport_spawn_decoy(self, vx: float, vy: float):
        wx, wy = self.tracker.camera.viewport_to_world(vx, vy)
        self.tracker.spawn_decoy(wx, wy)
        self.status_bar.showMessage(f"Optical decoy added at {wx:.0f}, {wy:.0f}.", 3000)

    def _on_minimap_designated(self, wx: float, wy: float):
        self.tracker.designate_target_at(wx, wy)
        self.status_bar.showMessage(f"Target designated at {wx:.0f}, {wy:.0f}.", 3000)

    def _on_minimap_spawn_decoy(self, wx: float, wy: float):
        self.tracker.spawn_decoy(wx, wy)
        self.status_bar.showMessage(f"Optical decoy added at {wx:.0f}, {wy:.0f}.", 3000)

    def _start_csv_logging(self, filename: str):
        if self.tracker.telemetry.start_logging(filename):
            self.status_bar.showMessage(f"Additional CSV recording started: {filename}", 4000)
        else:
            QMessageBox.warning(self, "Recording failed", "The selected CSV file could not be opened.")

    def _stop_csv_logging(self):
        self.tracker.telemetry.stop_logging()
        self.status_bar.showMessage("Additional CSV recording saved.", 4000)

    def _load_preset(self, preset_filename: str):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, "presets", preset_filename)
        try:
            self._set_running(False)
            if self.video_source:
                self.video_source.close()
                self.video_source = None
                self.minimap.show()
                self.source_button.setText("Open MP4")
                self.sim_timer.setInterval(round(1000 / self.tracker.cam_config.update_rate_hz))
            self.tracker.telemetry.finish_session()
            preset = self.tracker.load_preset(path)
            self.session_dir = self.tracker.telemetry.start_session(self.session_dir.parent)
            self.control_panel.refresh_from_tracker()
            self.minimap.set_references(self.tracker.primary_target, self.tracker.camera, self.tracker.secondary_targets)
            self.status_bar.showMessage(f"Scenario loaded: {preset.name}", 4000)
        except PresetError as exc:
            QMessageBox.warning(self, "Preset could not be loaded", str(exc))

    def _simulation_tick(self):
        now = time.perf_counter()
        dt = max(0.005, min(0.1, now - self.last_tick_time))
        self.last_tick_time = now
        detection = self.tracker.last_detection
        if self.is_running and self.video_source:
            frame = self.video_source.read()
            if frame is None:
                self._set_running(False)
                self.tracker.telemetry.finish_session()
                self.desktop.navigate(3)
                self.status_bar.showMessage("Video evaluation complete. Run reports are ready.")
            else:
                detection = self.tracker.step_external_frame(frame, 1.0 / self.video_source.fps)
        elif self.is_running:
            detection = self.tracker.step(dt)
        state = self.tracker.state if self.is_running else TrackingState.IDLE
        telemetry = self.tracker.telemetry
        self.viewport.update_frame(
            frame_np=self.tracker.current_frame, detection=detection,
            pred_x=self.tracker.latest_pred_x, pred_y=self.tracker.latest_pred_y,
            state=state, pan_deg=self.tracker.camera.pan_deg, tilt_deg=self.tracker.camera.tilt_deg,
            fps=telemetry.current_fps if self.is_running else 0.0,
            latency_ms=telemetry.pipeline_latency_ms, error_px=telemetry.current_error_px,
            rms_error_px=telemetry.rms_error_px,
        )
        self.minimap.update()
        self.telemetry_bar.update_metrics(
            current_error=telemetry.current_error_px, rms_error=telemetry.rms_error_px,
            acq_time=telemetry.acquisition_time_s, has_acq=telemetry.has_first_acquisition,
            loss_pct=telemetry.target_loss_pct, reacq_time=telemetry.last_reacquisition_time_s,
            fps=telemetry.current_fps if self.is_running else 0.0, state=state,
        )
        self.charts.update_data(
            times=telemetry.history_time, errors=telemetry.history_error,
            pans=telemetry.history_pan, tilts=telemetry.history_tilt,
            fps_list=telemetry.history_fps, speeds=telemetry.history_speed,
        )
        if self.is_running:
            locked = self.tracker.state == TrackingState.TRACKING
            self.phase_labels[2].setObjectName("phaseActive" if locked else "phaseIdle")
            self.phase_labels[3].setObjectName("phaseActive" if telemetry.total_frames else "phaseIdle")
            self.engine_badge.setText(self.tracker.state.value)
            for label in self.phase_labels[2:]:
                label.style().unpolish(label)
                label.style().polish(label)

    def closeEvent(self, event):
        self.sim_timer.stop()
        if self.video_source:
            self.video_source.close()
        self.tracker.telemetry.stop_logging()
        self.tracker.telemetry.finish_session()
        event.accept()
