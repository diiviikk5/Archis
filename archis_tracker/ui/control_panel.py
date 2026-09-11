"""
Archis Optical Tracker - Interactive Control Panel
Configures targets, camera motion limits, disturbance injection, and preset scenarios.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QLabel, QSlider, QComboBox, QCheckBox, QPushButton, 
                             QTabWidget, QSpinBox, QDoubleSpinBox, QGroupBox, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from ..core.config import (TargetShape, MotionTrajectory, AtmosphericCondition, 
                           PlatformMotionType)
from ..core.tracker import TrackingSystem


class ControlPanelWidget(QWidget):
    # Signals for parameter updates
    preset_selected_signal = pyqtSignal(str)
    reset_tracking_signal = pyqtSignal()
    toggle_autonomous_signal = pyqtSignal(bool)
    start_log_signal = pyqtSignal(str)
    stop_log_signal = pyqtSignal()

    def __init__(self, tracker: TrackingSystem, parent=None):
        super().__init__(parent)
        self.tracker = tracker
        self.setMinimumWidth(320)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(6)
        
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # 1. Target Tab
        self.tab_target = self._build_target_tab()
        self.tabs.addTab(self.tab_target, "Target")
        
        # 2. Camera Tab
        self.tab_camera = self._build_camera_tab()
        self.tabs.addTab(self.tab_camera, "Gimbal & Cam")
        
        # 3. Disturbances Tab
        self.tab_disturb = self._build_disturbances_tab()
        self.tabs.addTab(self.tab_disturb, "Disturbances")
        
        # 4. Scenarios & Logging Tab
        self.tab_presets = self._build_presets_tab()
        self.tabs.addTab(self.tab_presets, "Scenarios")

    def _build_target_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(10)
        
        # Target Shape (User-defined, default Square)
        box_shape = QGroupBox("Target Shape & Geometry")
        l_shape = QVBoxLayout(box_shape)
        self.combo_shape = QComboBox()
        for shape in TargetShape:
            self.combo_shape.addItem(shape.value, shape)
        self.combo_shape.setCurrentText(self.tracker.target_config.shape.value)
        self.combo_shape.currentIndexChanged.connect(self._on_shape_changed)
        l_shape.addWidget(QLabel("Target Shape (Default: Square):"))
        l_shape.addWidget(self.combo_shape)
        
        # Target Size (5-20 pixels)
        l_size = QHBoxLayout()
        self.lbl_size = QLabel(f"Size: {self.tracker.target_config.size}x{self.tracker.target_config.size} px")
        self.slider_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_size.setRange(5, 20)
        self.slider_size.setValue(self.tracker.target_config.size)
        self.slider_size.valueChanged.connect(self._on_size_changed)
        l_size.addWidget(self.lbl_size)
        l_size.addWidget(self.slider_size)
        l_shape.addLayout(l_size)
        layout.addWidget(box_shape)
        
        # Motion Trajectory (At least 4: Straight Line, Circular, Figure of 8, Random)
        box_motion = QGroupBox("Target Motion Trajectory")
        l_motion = QVBoxLayout(box_motion)
        self.combo_traj = QComboBox()
        for traj in MotionTrajectory:
            self.combo_traj.addItem(traj.value, traj)
        self.combo_traj.setCurrentText(self.tracker.target_config.trajectory.value)
        self.combo_traj.currentIndexChanged.connect(self._on_traj_changed)
        l_motion.addWidget(QLabel("Trajectory Pattern:"))
        l_motion.addWidget(self.combo_traj)
        
        # Target Speed
        l_spd = QHBoxLayout()
        self.lbl_spd = QLabel(f"Speed: {self.tracker.target_config.speed:.0f} px/s")
        self.slider_spd = QSlider(Qt.Orientation.Horizontal)
        self.slider_spd.setRange(10, 150)
        self.slider_spd.setValue(int(self.tracker.target_config.speed))
        self.slider_spd.valueChanged.connect(self._on_speed_changed)
        l_spd.addWidget(self.lbl_spd)
        l_spd.addWidget(self.slider_spd)
        l_motion.addLayout(l_spd)
        layout.addWidget(box_motion)
        
        # Multiple Targets Toggle
        box_multi = QGroupBox("Multiple Targets (Optional)")
        l_multi = QVBoxLayout(box_multi)
        self.chk_decoy = QCheckBox("Spawn Decoy Secondary Target")
        self.chk_decoy.toggled.connect(self._on_decoy_toggled)
        l_multi.addWidget(self.chk_decoy)
        layout.addWidget(box_multi)
        
        # Reset Target
        btn_reset_tgt = QPushButton("Reposition Target to Center")
        btn_reset_tgt.clicked.connect(lambda: self.tracker.primary_target.reset_position(1000.0, 1000.0))
        layout.addWidget(btn_reset_tgt)
        
        layout.addStretch()
        return w

    def _build_camera_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(10)
        
        # Pan/Tilt Motion Constraints (5-10 °/s, default 5 °/s)
        box_gimbal = QGroupBox("Gimbal Speed Constraints")
        l_gimbal = QVBoxLayout(box_gimbal)
        
        # Max Pan Speed
        l_pan = QHBoxLayout()
        self.lbl_pan_spd = QLabel(f"Max Pan Speed: {self.tracker.cam_config.max_pan_speed_deg_s:.1f} °/s")
        self.slider_pan_spd = QSlider(Qt.Orientation.Horizontal)
        self.slider_pan_spd.setRange(50, 100)
        self.slider_pan_spd.setValue(int(self.tracker.cam_config.max_pan_speed_deg_s * 10))
        self.slider_pan_spd.valueChanged.connect(self._on_pan_spd_changed)
        l_pan.addWidget(self.lbl_pan_spd)
        l_pan.addWidget(self.slider_pan_spd)
        l_gimbal.addLayout(l_pan)
        
        # Max Tilt Speed
        l_tilt = QHBoxLayout()
        self.lbl_tilt_spd = QLabel(f"Max Tilt Speed: {self.tracker.cam_config.max_tilt_speed_deg_s:.1f} °/s")
        self.slider_tilt_spd = QSlider(Qt.Orientation.Horizontal)
        self.slider_tilt_spd.setRange(50, 100)
        self.slider_tilt_spd.setValue(int(self.tracker.cam_config.max_tilt_speed_deg_s * 10))
        self.slider_tilt_spd.valueChanged.connect(self._on_tilt_spd_changed)
        l_tilt.addWidget(self.lbl_tilt_spd)
        l_tilt.addWidget(self.slider_tilt_spd)
        l_gimbal.addLayout(l_tilt)
        layout.addWidget(box_gimbal)
        
        # Closed-Loop Control Mode
        box_ctrl = QGroupBox("Tracking Controller")
        l_ctrl = QVBoxLayout(box_ctrl)
        self.chk_auto = QCheckBox("Autonomous Closed-Loop Tracking")
        self.chk_auto.setChecked(True)
        self.chk_auto.toggled.connect(self._on_auto_toggled)
        l_ctrl.addWidget(self.chk_auto)
        
        # Manual Jog controls
        l_jog = QGridLayout()
        btn_up = QPushButton("▲ Tilt Up")
        btn_down = QPushButton("▼ Tilt Down")
        btn_left = QPushButton("◄ Pan Left")
        btn_right = QPushButton("► Pan Right")
        
        btn_up.clicked.connect(lambda: self._manual_nudge(0.0, -0.5))
        btn_down.clicked.connect(lambda: self._manual_nudge(0.0, 0.5))
        btn_left.clicked.connect(lambda: self._manual_nudge(-0.5, 0.0))
        btn_right.clicked.connect(lambda: self._manual_nudge(0.5, 0.0))
        
        l_jog.addWidget(btn_up, 0, 1)
        l_jog.addWidget(btn_left, 1, 0)
        l_jog.addWidget(btn_right, 1, 2)
        l_jog.addWidget(btn_down, 2, 1)
        l_ctrl.addLayout(l_jog)
        layout.addWidget(box_ctrl)
        
        # Reset Gimbal
        btn_center_cam = QPushButton("Center Gimbal (Boresight Origin)")
        btn_center_cam.clicked.connect(self.tracker.camera.reset)
        layout.addWidget(btn_center_cam)
        
        layout.addStretch()
        return w

    def _build_disturbances_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(8)
        
        # 1. Atmospheric Disturbance (Clear, Haze, Fog, Rain, Low Light)
        box_atm = QGroupBox("Atmospheric Disturbance")
        l_atm = QVBoxLayout(box_atm)
        self.combo_atm = QComboBox()
        for atm in AtmosphericCondition:
            self.combo_atm.addItem(atm.value, atm)
        self.combo_atm.currentIndexChanged.connect(self._on_atm_changed)
        l_atm.addWidget(QLabel("Condition:"))
        l_atm.addWidget(self.combo_atm)
        
        # Severity slider
        l_sev = QHBoxLayout()
        self.lbl_sev = QLabel("Severity: 50%")
        self.slider_sev = QSlider(Qt.Orientation.Horizontal)
        self.slider_sev.setRange(10, 100)
        self.slider_sev.setValue(50)
        self.slider_sev.valueChanged.connect(self._on_atm_sev_changed)
        l_sev.addWidget(self.lbl_sev)
        l_sev.addWidget(self.slider_sev)
        l_atm.addLayout(l_sev)
        layout.addWidget(box_atm)
        
        # 2. Image Noise (Salt & Pepper, Gaussian, Poisson)
        box_noise = QGroupBox("Image Noise (User Selectable)")
        l_noise = QVBoxLayout(box_noise)
        
        self.chk_sp = QCheckBox("Salt & Pepper Noise (~10%)")
        self.chk_sp.toggled.connect(lambda v: setattr(self.tracker.disturb_config, "enable_salt_pepper", v))
        l_noise.addWidget(self.chk_sp)
        
        self.chk_gauss = QCheckBox("Gaussian Noise (Std Dev <= 20 px)")
        self.chk_gauss.toggled.connect(lambda v: setattr(self.tracker.disturb_config, "enable_gaussian_noise", v))
        l_noise.addWidget(self.chk_gauss)
        
        self.chk_poisson = QCheckBox("Poisson Shot Noise")
        self.chk_poisson.toggled.connect(lambda v: setattr(self.tracker.disturb_config, "enable_poisson_noise", v))
        l_noise.addWidget(self.chk_poisson)
        layout.addWidget(box_noise)
        
        # 3. Dynamic Motion Disturbances (Jitter & Platform)
        box_dyn = QGroupBox("Vibrations & Jitter (+-20 px/frame)")
        l_dyn = QVBoxLayout(box_dyn)
        
        self.chk_jitter = QCheckBox("Camera Jitter (+-8 px)")
        self.chk_jitter.toggled.connect(lambda v: setattr(self.tracker.disturb_config, "enable_camera_jitter", v))
        l_dyn.addWidget(self.chk_jitter)
        
        self.chk_plat = QCheckBox("Platform Dynamic Motion (+-5 px)")
        self.chk_plat.toggled.connect(lambda v: setattr(self.tracker.disturb_config, "enable_platform_motion", v))
        l_dyn.addWidget(self.chk_plat)
        layout.addWidget(box_dyn)
        
        layout.addStretch()
        return w

    def _build_presets_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(10)
        
        # Preset Operational Scenarios
        box_pre = QGroupBox("Operational Presets")
        l_pre = QVBoxLayout(box_pre)
        
        presets = [
            ("Nominal LEO Pass", "Clean sky, Figure-8 target, nominal jitter"),
            ("Heavy Atmospheric Turbulence", "Fog, Gaussian noise, contrast loss"),
            ("Platform Vibration Shock", "+-15px Jitter + Harmonic platform motion"),
            ("Cloud Dropout & Relock", "Low light, target obscuration, relock test"),
            ("High-Speed Evasive Target", "Rapid Brownian direction changes")
        ]
        
        for name, desc in presets:
            btn = QPushButton(name)
            btn.setToolTip(desc)
            btn.clicked.connect(lambda checked, n=name: self._apply_preset(n))
            l_pre.addWidget(btn)
            
        layout.addWidget(box_pre)
        
        # Telemetry Data Logging
        box_log = QGroupBox("Telemetry CSV Logger")
        l_log = QVBoxLayout(box_log)
        self.btn_log = QPushButton("Start Recording CSV Log")
        self.btn_log.clicked.connect(self._toggle_logging)
        l_log.addWidget(self.btn_log)
        
        self.lbl_log_status = QLabel("Status: Idle")
        self.lbl_log_status.setStyleSheet("color: #94a3b8; font-size: 10px;")
        l_log.addWidget(self.lbl_log_status)
        layout.addWidget(box_log)
        
        # Reset Session
        btn_reset_all = QPushButton("Reset All Performance Metrics")
        btn_reset_all.setObjectName("actionButton")
        btn_reset_all.clicked.connect(self._on_reset_all)
        layout.addWidget(btn_reset_all)
        
        layout.addStretch()
        return w

    # --- Event Handlers ---
    def _on_shape_changed(self, idx):
        shape = self.combo_shape.itemData(idx)
        self.tracker.primary_target.shape = shape
        self.tracker.target_config.shape = shape

    def _on_size_changed(self, val):
        self.lbl_size.setText(f"Size: {val}x{val} px")
        self.tracker.primary_target.size = val
        self.tracker.target_config.size = val

    def _on_traj_changed(self, idx):
        traj = self.combo_traj.itemData(idx)
        self.tracker.primary_target.trajectory = traj
        self.tracker.target_config.trajectory = traj

    def _on_speed_changed(self, val):
        self.lbl_spd.setText(f"Speed: {val} px/s")
        self.tracker.primary_target.speed = float(val)
        self.tracker.target_config.speed = float(val)

    def _on_decoy_toggled(self, checked):
        if checked:
            from ..core.target import TargetBeacon, TargetConfig, MotionTrajectory, TargetShape
            cfg = TargetConfig(shape=TargetShape.CIRCLE, size=8, trajectory=MotionTrajectory.CIRCULAR, speed=35.0, initial_x=1150.0, initial_y=950.0)
            decoy = TargetBeacon(1, cfg, is_primary=False)
            self.tracker.secondary_targets = [decoy]
        else:
            self.tracker.secondary_targets.clear()

    def _on_pan_spd_changed(self, val):
        spd = val / 10.0
        self.lbl_pan_spd.setText(f"Max Pan Speed: {spd:.1f} °/s")
        self.tracker.camera.max_pan_speed_deg_s = spd

    def _on_tilt_spd_changed(self, val):
        spd = val / 10.0
        self.lbl_tilt_spd.setText(f"Max Tilt Speed: {spd:.1f} °/s")
        self.tracker.camera.max_tilt_speed_deg_s = spd

    def _on_auto_toggled(self, checked):
        self.tracker.is_autonomous_tracking = checked
        self.toggle_autonomous_signal.emit(checked)

    def _manual_nudge(self, d_pan: float, d_tilt: float):
        self.tracker.camera.pan_deg += d_pan
        self.tracker.camera.tilt_deg += d_tilt
        self.tracker.camera.update_world_position()

    def _on_atm_changed(self, idx):
        atm = self.combo_atm.itemData(idx)
        self.tracker.disturb_config.atmospheric_condition = atm

    def _on_atm_sev_changed(self, val):
        sev = val / 100.0
        self.lbl_sev.setText(f"Severity: {val}%")
        self.tracker.disturb_config.atmospheric_severity = sev

    def _apply_preset(self, name: str):
        if name == "Nominal LEO Pass":
            self.combo_atm.setCurrentIndex(0)
            self.chk_sp.setChecked(False)
            self.chk_gauss.setChecked(False)
            self.chk_jitter.setChecked(False)
            self.combo_traj.setCurrentText(MotionTrajectory.FIGURE_OF_8.value)
            self.slider_spd.setValue(45)
            
        elif name == "Heavy Turbulence & Fog":
            self.combo_atm.setCurrentText(AtmosphericCondition.FOG.value)
            self.slider_sev.setValue(65)
            self.chk_gauss.setChecked(True)
            self.tracker.disturb_config.gaussian_noise_std = 12.0
            
        elif name == "Platform Vibration Shock":
            self.chk_jitter.setChecked(True)
            self.tracker.disturb_config.max_camera_jitter_px = 15.0
            self.chk_plat.setChecked(True)
            self.tracker.disturb_config.platform_motion_amplitude_px = 12.0
            
        elif name == "Cloud Dropout & Relock":
            self.combo_atm.setCurrentText(AtmosphericCondition.LOW_LIGHT.value)
            self.slider_sev.setValue(85)
            self.chk_sp.setChecked(True)
            
        elif name == "High-Speed Evasive Target":
            self.combo_traj.setCurrentText(MotionTrajectory.RANDOM.value)
            self.slider_spd.setValue(90)
            
        self.preset_selected_signal.emit(name)

    def _toggle_logging(self):
        if not self.tracker.telemetry.is_logging:
            path, _ = QFileDialog.getSaveFileName(self, "Save Telemetry CSV", "archis_telemetry.csv", "CSV Files (*.csv)")
            if path:
                if self.tracker.telemetry.start_csv_log(path):
                    self.btn_log.setText("Stop Recording CSV")
                    self.btn_log.setStyleSheet("background-color: #f43f5e; color: white;")
                    self.lbl_log_status.setText(f"Recording: {os.path.basename(path)}")
        else:
            self.tracker.telemetry.stop_csv_log()
            self.btn_log.setText("Start Recording CSV Log")
            self.btn_log.setStyleSheet("")
            self.lbl_log_status.setText("Status: Log Saved")

    def _on_reset_all(self):
        self.tracker.reset()
        self.reset_tracking_signal.emit()
