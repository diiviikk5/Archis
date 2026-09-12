"""
Primary desktop operator workspace for Archis optical tracking.
Built with Microsoft Windows 11 Fluent Design Architecture (MSFluentWindow).
"""
from __future__ import annotations

import os
import time

from PyQt6.QtCore import QSettings, QStandardPaths, Qt, QTimer, QUrl
from PyQt6.QtGui import QAction, QDesktopServices, QIcon
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from qfluentwidgets import (
    FluentWindow, FluentIcon as FIF, NavigationItemPosition,
    InfoBar, InfoBarPosition, NavigationAvatarWidget,
)

from ..core.config import TrackingState
from ..core.presets import PresetError
from ..core.tracker import TrackingSystem
from ..core.video_source import VideoSource, VideoSourceError
from .control_panel import ControlPanelWidget
from .onboarding import OnboardingDialog
from .style import DARK_THEME_QSS, init_fluent_theme
from .workspaces import (
    HomeInterface, SetupInterface, TrackingInterface, ReviewInterface,
)


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        init_fluent_theme()
        self.setWindowTitle("Archis Optical Tracking Console")
        self.resize(1500, 940)
        self.setMinimumSize(1160, 740)
        self.setStyleSheet(DARK_THEME_QSS)

        # Assets & window icon
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
        self.logo_path = os.path.join(assets_dir, "logo.png")
        if os.path.exists(self.logo_path):
            self.setWindowIcon(QIcon(self.logo_path))

        self.settings = QSettings("Archis", "OpticalTracker")
        self.tracker = TrackingSystem()
        self.is_running = False
        self.video_source = None
        self.was_locked = False

        # Sidebar navigation configuration - spacious, unclipped, expandable
        self.navigationInterface.setMenuButtonVisible(True)
        self.navigationInterface.setReturnButtonVisible(False)
        self.navigationInterface.setExpandWidth(250)
        self.navigationInterface.setMinimumExpandWidth(220)

        reports_root = os.path.join(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation),
            "Archis Tracker", "Reports",
        )
        self.session_dir = self.tracker.telemetry.start_session(reports_root)

        # Embedded control panel holding backend widgets
        self.control_panel = ControlPanelWidget(self.tracker)
        self.control_panel.preset_selected_signal.connect(self._load_preset)
        self.control_panel.start_log_signal.connect(self._start_csv_logging)
        self.control_panel.stop_log_signal.connect(self._stop_csv_logging)
        self.control_panel.hide()

        # Build modular sub-interfaces
        self.home_interface = HomeInterface(self)
        self.setup_interface = SetupInterface(self)
        self.tracking_interface = TrackingInterface(self)
        self.review_interface = ReviewInterface(self)

        # Map tracking handles
        self.telemetry_bar = self.tracking_interface.telemetry_bar
        self.viewport = self.tracking_interface.viewport
        self.minimap = self.tracking_interface.minimap
        self.charts = self.tracking_interface.charts
        self.run_button = self.tracking_interface.run_button
        self.reset_button = self.tracking_interface.reset_button
        self.source_button = self.tracking_interface.source_button
        self.engine_badge = self.tracking_interface.engine_badge

        # Register sub-interfaces with FluentWindow
        self.addSubInterface(self.home_interface, FIF.HOME, "Home Operations")
        self.addSubInterface(self.setup_interface, FIF.SETTING, "Mission Setup")
        self.addSubInterface(self.tracking_interface, FIF.CAMERA, "Live Optical Tracking")
        self.addSubInterface(self.review_interface, FIF.DOCUMENT, "Review & Audit")

        # Bottom navigation utility items
        self.navigationInterface.addItem(
            routeKey="quickstart",
            icon=FIF.HELP,
            text="Quick Start Guide",
            onClick=self._show_onboarding,
            position=NavigationItemPosition.BOTTOM,
        )
        self.navigationInterface.addItem(
            routeKey="evidence",
            icon=FIF.FOLDER,
            text="Evidence Reports",
            onClick=self._open_reports,
            position=NavigationItemPosition.BOTTOM,
        )

        # Station identity avatar badge in navigation pane
        if os.path.exists(self.logo_path):
            self.station_avatar = NavigationAvatarWidget("ARCHIS FSOC Station", self.logo_path, self)
            self.navigationInterface.addWidget(
                routeKey="station_avatar",
                widget=self.station_avatar,
                position=NavigationItemPosition.BOTTOM,
            )

        # Expand navigation sidebar by default so typography is open and clear
        self.navigationInterface.expand(useAni=False)

        self._build_shortcuts()

        # Simulation tick timer (30 Hz minimum)
        self.sim_timer = QTimer(self)
        self.playback_scale = 1.0
        self.sim_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.sim_timer.timeout.connect(self._simulation_tick)
        self.last_tick_time = time.perf_counter()
        self.sim_timer.start(round(1000.0 / self.tracker.cam_config.update_rate_hz))
        self._update_run_state()

        if not self.settings.value("onboarding_complete", False, type=bool):
            QTimer.singleShot(250, self._show_onboarding)

    def show_info_toast(self, title: str, content: str):
        InfoBar.info(title=title, content=content, duration=3500, parent=self, position=InfoBarPosition.TOP_RIGHT)

    def show_success_toast(self, title: str, content: str):
        InfoBar.success(title=title, content=content, duration=3000, parent=self, position=InfoBarPosition.TOP_RIGHT)

    def show_warning_toast(self, title: str, content: str):
        InfoBar.warning(title=title, content=content, duration=3500, parent=self, position=InfoBarPosition.TOP_RIGHT)

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
            self.switchTo(self.tracking_interface)
        self.last_tick_time = time.perf_counter()
        self._update_run_state()

    def _update_run_state(self):
        if self.is_running:
            self.run_button.setIcon(FIF.PAUSE.icon())
            self.run_button.setText(" Pause Run")
            self.engine_badge.setText(f"PAT STATE: {self.tracker.state.value}")
            self.engine_badge.setStyleSheet("color: #34d399; background-color: #062319; border: 1px solid #059669; border-radius: 6px; padding: 6px 12px; font: 700 11px Consolas, monospace;")
        else:
            self.run_button.setIcon(FIF.PLAY.icon())
            self.run_button.setText(" Start Run")
            self.engine_badge.setText("PAT STATE: ENGINE READY")
            self.engine_badge.setStyleSheet("color: #38bdf8; background-color: #082032; border: 1px solid #0284c7; border-radius: 6px; padding: 6px 12px; font: 700 11px Consolas, monospace;")

    def _reset_run(self):
        self._set_running(False)
        self.tracker.telemetry.finish_session()
        self.tracker.reset()
        self.session_dir = self.tracker.telemetry.start_session(self.session_dir.parent)
        if self.video_source:
            self.video_source.rewind()
        self.charts.clear_data()
        self.show_info_toast("Run Reset", "Tracker reset to initial conditions. Scenarios preserved.")

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
            self.show_warning_toast("Video Error", str(exc))
            return
        if self.video_source:
            self.video_source.close()
        self.video_source = source
        self._set_running(False)
        self.tracker.telemetry.finish_session()
        self.tracker.reset()
        self.session_dir = self.tracker.telemetry.start_session(self.session_dir.parent)
        self.minimap.hide()
        self.switchTo(self.tracking_interface)
        self._set_playback_speed(self.tracking_interface.playback_speed.currentIndex())
        self.source_button.setText(" " + source.path.name[:16])
        self.show_info_toast(
            "Video Input Connected",
            f"Loaded {source.path.name} ({source.width}x{source.height} @ {source.fps:.1f} FPS)",
        )

    def _on_viewport_designated(self, vx: float, vy: float):
        wx, wy = self.tracker.camera.viewport_to_world(vx, vy)
        self.tracker.designate_target_at(wx, wy)
        self.show_info_toast("Target Designated", f"Boresight target locked at world {wx:.0f}, {wy:.0f}.")

    def _on_viewport_spawn_decoy(self, vx: float, vy: float):
        wx, wy = self.tracker.camera.viewport_to_world(vx, vy)
        self.tracker.spawn_decoy(wx, wy)
        self.show_warning_toast("Optical Decoy Injected", f"Secondary spot spawned at world {wx:.0f}, {wy:.0f}.")

    def _on_minimap_designated(self, wx: float, wy: float):
        self.tracker.designate_target_at(wx, wy)
        self.show_info_toast("Target Designated", f"Radar designation moved to {wx:.0f}, {wy:.0f}.")

    def _on_minimap_spawn_decoy(self, wx: float, wy: float):
        self.tracker.spawn_decoy(wx, wy)
        self.show_warning_toast("Optical Decoy Injected", f"Secondary spot spawned at {wx:.0f}, {wy:.0f}.")

    def _start_csv_logging(self, filename: str):
        if self.tracker.telemetry.start_logging(filename):
            self.show_success_toast("CSV Logging Started", f"Recording session telemetry to {filename}")
        else:
            QMessageBox.warning(self, "Recording failed", "The selected CSV file could not be opened.")

    def _stop_csv_logging(self):
        self.tracker.telemetry.stop_logging()
        self.show_info_toast("CSV Logging Saved", "Telemetry file closed successfully.")

    def _load_preset(self, preset_filename: str):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, "presets", preset_filename)
        try:
            self._set_running(False)
            if self.video_source:
                self.video_source.close()
                self.video_source = None
                self.minimap.show()
                self.source_button.setText(" Video Input")
                self._set_playback_speed(self.tracking_interface.playback_speed.currentIndex())
            self.tracker.telemetry.finish_session()
            preset = self.tracker.load_preset(path)
            self.session_dir = self.tracker.telemetry.start_session(self.session_dir.parent)
            self.control_panel.refresh_from_tracker()
            self.minimap.set_references(self.tracker.primary_target, self.tracker.camera, self.tracker.secondary_targets)
            self.show_success_toast("Mission Preset Loaded", f"Configured scenario: {preset.name}")
        except PresetError as exc:
            self.show_warning_toast("Preset Error", str(exc))

    def _set_playback_speed(self, index):
        self.playback_scale = (0.25, 0.5, 1.0)[index]
        rate = self.video_source.fps if self.video_source else self.tracker.cam_config.update_rate_hz
        self.sim_timer.setInterval(max(1, round(1000.0 / rate / self.playback_scale)))

    def _simulation_tick(self):
        now = time.perf_counter()
        # One sensor period per frame: UI stalls must not teleport the target.
        dt = 1.0 / self.tracker.cam_config.update_rate_hz
        self.last_tick_time = now
        detection = self.tracker.last_detection
        if self.is_running and self.video_source:
            frame = self.video_source.read()
            if frame is None:
                self._set_running(False)
                self.tracker.telemetry.finish_session()
                self.switchTo(self.review_interface)
                self.show_info_toast("Video Complete", "Video evaluation completed. Audit reports ready.")
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
            if locked and not self.was_locked:
                self.was_locked = True
                self.show_success_toast(
                    "Optical Lock Acquired",
                    "Beacon acquisition verified within steady-state error tolerance.",
                )
            elif not locked and self.tracker.state == TrackingState.LOST and self.was_locked:
                self.was_locked = False
                self.show_warning_toast(
                    "Target Loss Detected",
                    "Beacon departed sensor FOV or obscured by disturbance.",
                )
            self.engine_badge.setText(f"PAT STATE: {self.tracker.state.value}")

    def closeEvent(self, event):
        self.sim_timer.stop()
        if self.video_source:
            self.video_source.close()
        self.tracker.telemetry.stop_logging()
        self.tracker.telemetry.finish_session()
        event.accept()
