"""Camera-first instrument workspace with measured telemetry and optional overlays."""
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter, QTabWidget,
    QFormLayout, QCheckBox, QFileDialog, QScrollArea,
)
from qfluentwidgets import ComboBox, PushButton, PrimaryPushButton, ToolButton, FluentIcon as FIF

from .viewport import ViewportWidget
from .minimap import MinimapWidget
from .charts import TelemetryChartsWidget
from ..core.config import TrackingState, TrackingAlgorithm


class LiveMetrics(QWidget):
    def __init__(self):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 10, 0, 10)
        self.values = {}
        for name in ("Pointing error", "RMS error", "Acquisition", "Target loss", "Sensor rate"):
            group = QVBoxLayout()
            label = QLabel(name)
            label.setObjectName("metricLabel")
            value = QLabel("--")
            value.setObjectName("metricValue")
            group.addWidget(label)
            group.addWidget(value)
            row.addLayout(group, 1)
            self.values[name] = value

    def update_metrics(self, current_error, rms_error, acq_time, has_acq,
                       loss_pct, reacq_time, fps, state):
        measured = has_acq
        values = {
            "Pointing error": f"{current_error:.2f} px" if measured else "--",
            "RMS error": f"{rms_error:.2f} px" if measured else "--",
            "Acquisition": f"{acq_time:.2f} s" if measured else "--",
            "Target loss": f"{loss_pct:.1f}%" if measured else "--",
            "Sensor rate": f"{fps:.1f} fps" if state != TrackingState.IDLE else "Paused",
        }
        for name, value in values.items():
            self.values[name].setText(value)


class TrackingInterface(QWidget):
    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window = window
        self.setObjectName("trackingInterface")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget#trackingInterface { background: #191a1c; color: #eceeef; }
            QLabel { color: #dfe1e3; font: 12px 'Segoe UI'; background: transparent; }
            QLabel#liveTitle { font-size: 19px; font-weight: 600; }
            QLabel#metricLabel { color: #9c9fa4; font-size: 11px; }
            QLabel#metricValue { color: #eceeef; font: 18px 'Consolas'; }
            QLabel#sourceLabel { color: #9c9fa4; }
            QTabWidget::pane { border: 0; background: #202123; }
            QTabBar::tab { background: transparent; color: #a9adb2; padding: 8px 12px; border: 0; }
            QTabBar::tab:selected { color: #f2f3f4; border-bottom: 2px solid #50bdd1; }
            QSplitter::handle { background: #353638; width: 1px; height: 1px; }
            QCheckBox { color: #c7cacf; spacing: 8px; padding: 4px 0; }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 16, 22, 12)
        root.setSpacing(12)
        heading = QHBoxLayout()
        title = QLabel("Live tracking")
        title.setObjectName("liveTitle")
        heading.addWidget(title)
        heading.addStretch()
        self.engine_badge = QLabel("Ready")
        self.engine_badge.setMinimumWidth(140)
        self.engine_badge.setAlignment(Qt.AlignmentFlag.AlignRight)
        heading.addWidget(self.engine_badge)
        root.addLayout(heading)

        transport = QHBoxLayout()
        transport.setSpacing(8)
        self.run_button = PrimaryPushButton(FIF.PLAY, "Start")
        self.run_button.setFixedWidth(94)
        self.run_button.clicked.connect(window._toggle_run)
        transport.addWidget(self.run_button)
        self.reset_button = self._tool(FIF.SYNC, "Reset run", window._reset_run)
        transport.addWidget(self.reset_button)
        self.source_button = PushButton(FIF.VIDEO, "Open video")
        self.source_button.setFixedWidth(130)
        self.source_button.clicked.connect(window._open_video)
        transport.addWidget(self.source_button)
        self.truth_button = PushButton(FIF.DOCUMENT, "Load truth")
        self.truth_button.setFixedWidth(110)
        self.truth_button.clicked.connect(window._open_truth)
        self.truth_button.setToolTip("CSV/JSON frame or timestamp centroid sidecar")
        transport.addWidget(self.truth_button)
        self.playback_speed = ComboBox()
        self.playback_speed.addItems(["0.25x", "0.5x", "1x real time"])
        self.playback_speed.setCurrentIndex(2)
        self.playback_speed.setFixedWidth(125)
        self.playback_speed.setToolTip("Playback pace; measurements retain sensor timing")
        self.playback_speed.currentIndexChanged.connect(window._set_playback_speed)
        transport.addWidget(self.playback_speed)
        transport.addStretch()
        self.capture_button = self._tool(FIF.SAVE, "Save sensor frame", self._capture)
        self.capture_button.setEnabled(False)
        transport.addWidget(self.capture_button)
        self.inspector_button = self._tool(FIF.SETTING, "Toggle inspector", self._toggle_inspector)
        transport.addWidget(self.inspector_button)
        root.addLayout(transport)
        self.telemetry_bar = LiveMetrics()
        root.addWidget(self.telemetry_bar)

        self.vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        self.vertical_splitter.setChildrenCollapsible(False)
        self.optical_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.optical_splitter.setChildrenCollapsible(False)
        camera = QWidget()
        camera_layout = QVBoxLayout(camera)
        camera_layout.setContentsMargins(0, 0, 0, 0)
        camera_layout.setSpacing(6)
        camera_header = QHBoxLayout()
        self.source_label = QLabel("Simulation / sensor feed")
        self.source_label.setObjectName("sourceLabel")
        camera_header.addWidget(self.source_label, 1)
        self.frame_label = QLabel("640 x 480")
        camera_header.addWidget(self.frame_label)
        camera_layout.addLayout(camera_header)
        self.viewport = ViewportWidget()
        self.viewport.designate_target_signal.connect(window._on_viewport_designated)
        self.viewport.spawn_decoy_signal.connect(window._on_viewport_spawn_decoy)
        camera_layout.addWidget(self.viewport, 1)
        self.optical_splitter.addWidget(camera)

        self.inspector = QTabWidget()
        self.inspector.setMinimumWidth(240)
        self.inspector.setMaximumWidth(285)
        details = QWidget()
        detail_layout = QVBoxLayout(details)
        detail_layout.setContentsMargins(14, 12, 14, 12)
        self.fields = {}
        form = QFormLayout()
        form.setVerticalSpacing(12)
        for name in ("Detector", "Model", "Post-filter", "Response", "Centroid", "Boresight Error", "SNR", "Pan / tilt", "Latency"):
            value = QLabel("--")
            value.setWordWrap(True)
            value.setMinimumWidth(100)
            form.addRow(name, value)
            self.fields[name] = value
        detail_layout.addLayout(form)
        detail_layout.addSpacing(16)
        detail_layout.addWidget(QLabel("Overlays"))
        self.overlay_controls = {}
        for text, attribute in (("Boresight", "show_crosshair"), ("Detection", "show_detection"),
                                ("Prediction", "show_prediction"), ("Error vector", "show_error_vector"),
                                ("Search gate", "show_gate"), ("Model heatmap", "show_heatmap")):
            checkbox = QCheckBox(text)
            checkbox.setChecked(getattr(self.viewport, attribute))
            checkbox.toggled.connect(lambda checked, attr=attribute: self._overlay(attr, checked))
            detail_layout.addWidget(checkbox)
            self.overlay_controls[attribute] = checkbox
        detail_layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(details)
        self.inspector.addTab(scroll, "Inspector")
        self.minimap = MinimapWidget()
        self.minimap.set_references(
            window.tracker.primary_target,
            window.tracker.camera,
            window.tracker.secondary_targets,
            window.tracker.world_model,
        )
        self.minimap.designate_world_signal.connect(window._on_minimap_designated)
        self.minimap.spawn_decoy_world_signal.connect(window._on_minimap_spawn_decoy)
        self.inspector.addTab(self.minimap, "World")
        self.optical_splitter.addWidget(self.inspector)
        self.optical_splitter.setStretchFactor(0, 1)
        self.vertical_splitter.addWidget(self.optical_splitter)
        self.charts = TelemetryChartsWidget()
        self.vertical_splitter.addWidget(self.charts)
        self.vertical_splitter.setStretchFactor(0, 4)
        self.vertical_splitter.setStretchFactor(1, 1)
        self.vertical_splitter.setSizes([600, 180])
        root.addWidget(self.vertical_splitter, 1)
        self.status_line = QLabel("No frames processed")
        self.status_line.setObjectName("sourceLabel")
        root.addWidget(self.status_line)

    def _tool(self, icon, title, callback):
        button = ToolButton(icon)
        button.setFixedSize(40, 40)
        button.setToolTip(title)
        button.setAccessibleName(title)
        button.clicked.connect(callback)
        return button

    def _overlay(self, attribute, checked):
        setattr(self.viewport, attribute, checked)
        self.viewport.update()

    def _toggle_inspector(self):
        self.inspector.setVisible(self.inspector.isHidden())

    def _capture(self):
        if self.viewport.frame_image is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save sensor frame", str(Path(self.window.session_dir) / "frame.png"), "PNG (*.png)")
        if path and not self.viewport.frame_image.save(path, "PNG"):
            self.window.show_warning_toast("Capture failed", "The image could not be written.")
        elif path:
            self.window.show_success_toast("Frame saved", Path(path).name)

    def refresh(self, detection):
        tracker = self.window.tracker
        if hasattr(self.window, "scenario_summary"):
            self.window.scenario_summary.refresh()
        source = self.window.video_source
        self.source_label.setText(source.path.name if source else "Simulation / sensor feed")
        self.source_label.setToolTip(str(source.path) if source else "Virtual optical sensor")
        self.frame_label.setText(f"{self.viewport.frame_width} x {self.viewport.frame_height}")
        self.inspector.setTabEnabled(1, source is None)
        if source and self.inspector.currentIndex() == 1:
            self.inspector.setCurrentIndex(0)
        self.fields["Detector"].setText(detection.algorithm_used if detection else "--")
        model = tracker.detector.ai_detector
        ai_active = tracker.detector.config.algorithm in (TrackingAlgorithm.AI_ONNX, TrackingAlgorithm.HYBRID)
        self.fields["Model"].setText(model.status if ai_active else "Not selected")
        self.fields["Model"].setToolTip(model.last_error or str(model.model_path))
        identity = tracker.last_result.diagnostics.get("identity_status") if tracker.last_result else None
        self.fields["Post-filter"].setText(identity or ("AI shape + temporal acquisition" if ai_active else "Temporal acquisition"))
        self.fields["Response"].setText(f"{detection.confidence:.3f}" if detection else "--")
        self.fields["Response"].setToolTip("Uncalibrated detector response, not a probability of correctness")
        self.fields["Centroid"].setText(f"({detection.x:.1f}, {detection.y:.1f}) px" if detection and detection.detected else "Not detected")
        center_x = self.viewport.frame_width / 2.0
        center_y = self.viewport.frame_height / 2.0
        self.fields["Centroid"].setToolTip(
            f"Native image coordinates. Boresight center is ({center_x:.1f}, {center_y:.1f})."
        )
        err_val = tracker.telemetry.current_error_px if detection and detection.detected else 0.0
        self.fields["Boresight Error"].setText(f"{err_val:.2f} px (<=10 px PASS)" if detection and detection.detected else "--")
        self.fields["Boresight Error"].setStyleSheet("color: #4ade80; font-weight: bold;" if err_val <= 10.0 else "color: #f87171;")
        self.fields["SNR"].setText(f"{detection.snr_db:.1f} dB" if detection and detection.detected else "--")
        command = tracker.last_result.command if tracker.last_result else None
        if source and command is not None:
            self.fields["Pan / tilt"].setText(
                f"theoretical {command.pan_rate_deg_s:+.2f} / {command.tilt_rate_deg_s:+.2f} deg/s"
            )
        else:
            self.fields["Pan / tilt"].setText(
                f"{tracker.camera.pan_deg:+.2f} / {tracker.camera.tilt_deg:+.2f} deg"
            )
        self.fields["Latency"].setText(f"{tracker.telemetry.pipeline_latency_ms:.2f} ms")
        self.capture_button.setEnabled(self.viewport.frame_image is not None)
        self.status_line.setText(f"{'Video' if source else 'Simulation'}  |  {tracker.telemetry.total_frames} frames  |  {self.window.playback_scale:g}x playback")
