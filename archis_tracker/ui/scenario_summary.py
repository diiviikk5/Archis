"""Live, read-only scenario summary for the expanded navigation rail."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import NavigationWidget


class ScenarioSummaryWidget(NavigationWidget):
    """Shows the active live-engine configuration in the navigation rail.

    This is deliberately a read-only view of the live objects rather than a
    second set of controls.  The Mission Setup screen remains the single place
    that mutates configuration, while this panel makes debugging unambiguous.
    """

    EXPANDED_HEIGHT = 390

    def __init__(self, window, parent=None):
        super().__init__(isSelectable=False, parent=parent)
        self.window = window
        self.setObjectName("scenarioSummary")
        self._signature: tuple[str, ...] | None = None
        self.fields: dict[str, QLabel] = {}

        self.content = QWidget(self)
        self.content.setObjectName("scenarioSummaryContent")
        root = QVBoxLayout(self.content)
        root.setContentsMargins(10, 10, 10, 12)
        root.setSpacing(7)

        title = QLabel("ACTIVE CONFIGURATION")
        title.setObjectName("scenarioSummaryTitle")
        root.addWidget(title)
        hint = QLabel("Live engine values · edit in Mission Setup")
        hint.setObjectName("scenarioSummaryHint")
        hint.setWordWrap(True)
        root.addWidget(hint)

        selected = QGridLayout()
        selected.setContentsMargins(0, 2, 0, 0)
        selected.setHorizontalSpacing(7)
        selected.setVerticalSpacing(5)
        for row, (key, label) in enumerate((
            ("Scenario", "Scenario"),
            ("Input", "Input"),
            ("Environment", "Environment"),
            ("Terminals", "3D terminals"),
            ("Target", "Target"),
            ("Disturbances", "Disturbances"),
            ("Dropout", "Dropout"),
            ("Detector", "Detector"),
            ("Camera", "Camera"),
            ("Control", "Control"),
        )):
            name = QLabel(label)
            name.setObjectName("scenarioSummaryKey")
            name.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            value = QLabel("--")
            value.setObjectName("scenarioSummaryValue")
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            selected.addWidget(name, row, 0)
            selected.addWidget(value, row, 1)
            selected.setColumnStretch(1, 1)
            self.fields[key] = value
        root.addLayout(selected)

        root.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content)
        self.setStyleSheet("""
            QWidget#scenarioSummaryContent {
                background: #111820;
                border: 1px solid #263343;
                border-radius: 7px;
            }
            QLabel#scenarioSummaryTitle {
                color: #67d4e8;
                font: 700 10px "Segoe UI";
                letter-spacing: 0.8px;
            }
            QLabel#scenarioSummaryHint {
                color: #718096;
                font: 9px "Segoe UI";
            }
            QLabel#scenarioSummaryKey {
                color: #8793a4;
                font: 9px "Segoe UI";
                min-width: 58px;
                max-width: 58px;
            }
            QLabel#scenarioSummaryValue {
                color: #e1e7ef;
                font: 9px "Consolas";
            }
        """)
        self.refresh(force=True)

    @staticmethod
    def _on_off(enabled: bool) -> str:
        return "ON" if enabled else "off"

    def refresh(self, force: bool = False) -> None:
        tracker = self.window.tracker
        target = tracker.primary_target
        disturbance = tracker.disturb_config
        detector = tracker.detector.config
        camera = tracker.cam_config
        controller = tracker.ctrl_config
        world = tracker.world_snapshot

        preset_path = Path(self.window.current_preset_path)
        preset_name = preset_path.stem.replace("_", " ").title()
        if self.window.video_source:
            source_name = f"Video · {self.window.video_source.path.name}"
        else:
            source_name = "Deterministic simulation"

        environment = (
            f"{tracker.env_config.screen_width}×{tracker.env_config.screen_height}; "
            f"{disturbance.atmospheric_condition.value} {disturbance.atmospheric_severity:.0%}; "
            f"seed {disturbance.random_seed}"
        )
        terminals = (
            f"RX ({world.receiver.position_m.x:.0f}, {world.receiver.position_m.y:.0f}, "
            f"{world.receiver.position_m.z:.0f}) m; TX range {world.separation_m:.0f} m; "
            f"decoys {len(world.decoys)}"
        )
        target_text = (
            f"{target.shape.value}, {target.size}px, {target.trajectory.value}; "
            f"{target.speed:.0f}px/s, intensity {target.intensity:.0f}"
        )

        noise = []
        if disturbance.enable_gaussian_noise:
            noise.append(f"Gaussian σ{disturbance.gaussian_noise_std:g}")
        if disturbance.enable_poisson_noise:
            noise.append("Poisson")
        if disturbance.enable_salt_pepper:
            noise.append(f"salt/pepper {disturbance.salt_pepper_ratio:.1%}")
        if disturbance.enable_camera_jitter:
            noise.append(f"jitter ±{disturbance.max_camera_jitter_px:g}px")
        if disturbance.enable_platform_motion:
            noise.append(
                f"platform {disturbance.platform_motion_type.value} "
                f"±{disturbance.platform_motion_amplitude_px:g}px"
            )
        if disturbance.turbulence_warp_px > 0:
            noise.append(f"warp {disturbance.turbulence_warp_px:g}px")
        if disturbance.turbulence_blur_sigma_px > 0:
            noise.append(f"blur σ{disturbance.turbulence_blur_sigma_px:g}px")
        if disturbance.scintillation_model == "gamma_gamma" and disturbance.rytov_variance > 0:
            noise.append(f"Gamma–Gamma Rytov {disturbance.rytov_variance:g}")
        elif disturbance.scintillation_log_std > 0:
            noise.append(f"scint σ{disturbance.scintillation_log_std:g}")
        if disturbance.illumination_flicker_fraction > 0:
            noise.append(
                f"flicker {disturbance.illumination_flicker_fraction:.0%} "
                f"@{disturbance.illumination_flicker_hz:g}Hz"
            )
        disturbances = "; ".join(noise) if noise else "None enabled"

        dropout_modes = []
        if disturbance.dropout_enabled:
            dropout_modes.append(
                f"scheduled {disturbance.dropout_start_s:g}s +"
                f"{disturbance.dropout_duration_s:g}s"
            )
        if disturbance.dropout_burst_enabled:
            dropout_modes.append(
                f"burst clear/loss {disturbance.dropout_mean_clear_s:g}/"
                f"{disturbance.dropout_mean_loss_s:g}s"
            )
        dropout = "; ".join(dropout_modes) if dropout_modes else "Disabled"

        code = detector.code_lock_pattern or "off"
        detector_text = (
            f"{detector.algorithm.value}; {detector.agc_mode.value}; "
            f"gate {self._on_off(detector.enable_track_gate)} {detector.gate_size_px}px; "
            f"FWHM {'adaptive' if detector.enable_scale_relative_geometry else 'fixed'} "
            f"{tracker.detector.spot_scale_px:.1f}px; R-cal {detector.measurement_noise_calibration:g}; "
            f"CodeLock {code}"
        )
        stabilizer = (
            f"ON (σ{camera.inertial_sensor_noise_px:g}px)"
            if camera.inertial_stabilization_enabled else "off"
        )
        camera_text = (
            f"{camera.viewport_width}×{camera.viewport_height} @{camera.update_rate_hz:g}Hz; "
            f"FOV {camera.fov_x_deg:g}°×{camera.fov_y_deg:g}°; "
            f"rate {camera.max_pan_speed_deg_s:g}/{camera.max_tilt_speed_deg_s:g}°/s; "
            f"inertial stabilizer {stabilizer}"
        )
        control_text = (
            f"{'Autonomous' if tracker.is_autonomous_tracking else 'Manual'}; "
            f"PID P/I/D {controller.kp_pan:g}/{controller.ki_pan:g}/{controller.kd_pan:g}; "
            f"latency {controller.latency_compensation_s:g}s; {tracker.canonical_state.value.upper()}"
        )
        values = {
            "Scenario": preset_name,
            "Input": source_name,
            "Environment": environment,
            "Terminals": terminals,
            "Target": target_text,
            "Disturbances": disturbances,
            "Dropout": dropout,
            "Detector": detector_text,
            "Camera": camera_text,
            "Control": control_text,
        }
        signature = tuple(values.values())
        if not force and signature == self._signature:
            return
        self._signature = signature
        for name, value in values.items():
            self.fields[name].setText(value)
            self.fields[name].setToolTip(value)

    def field_text(self, name: str) -> str:
        """Test/debug helper returning the text currently shown for a field."""
        return self.fields[name].text()

    def setCompacted(self, isCompacted: bool) -> None:
        self.isCompacted = isCompacted
        self.content.setVisible(not isCompacted)
        if isCompacted:
            self.setFixedSize(40, 36)
        else:
            self.setFixedSize(self.EXPAND_WIDTH, self.EXPANDED_HEIGHT)
