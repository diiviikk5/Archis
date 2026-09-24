"""
Archis Optical Tracker - Interactive Control Panel
Configures targets, camera motion limits, disturbance injection,
optics tracking algorithms, and preset aerospace mission scenarios.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QLabel, QSlider, QComboBox, QCheckBox, QPushButton, QLineEdit,
                             QTabWidget, QSpinBox, QDoubleSpinBox, QGroupBox, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
import numpy as np
from ..core.config import (TargetShape, MotionTrajectory, AtmosphericCondition, 
                           PlatformMotionType, TrackingAlgorithm, AGCMode)
from ..core.tracker import TrackingSystem


class ControlPanelWidget(QWidget):
    preset_selected_signal = pyqtSignal(str)
    reset_tracking_signal = pyqtSignal()
    toggle_autonomous_signal = pyqtSignal(bool)
    start_log_signal = pyqtSignal(str)
    stop_log_signal = pyqtSignal()

    def __init__(self, tracker: TrackingSystem, parent=None):
        super().__init__(parent)
        self.tracker = tracker
        self.setMinimumWidth(330)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(6)
        
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # 1. Target Tab
        self.tab_target = self._build_target_tab()
        self.tabs.addTab(self.tab_target, "Target")
        
        # 2. Optics & Algorithms Tab (NEW)
        self.tab_optics = self._build_optics_tab()
        self.tabs.addTab(self.tab_optics, "Optics & Algo")
        
        # 3. Camera & Gimbal Tab
        self.tab_camera = self._build_camera_tab()
        self.tabs.addTab(self.tab_camera, "Gimbal")
        
        # 4. Disturbances Tab
        self.tab_disturb = self._build_disturbances_tab()
        self.tabs.addTab(self.tab_disturb, "Disturbances")
        
        # 5. Scenarios & Logging Tab
        self.tab_presets = self._build_presets_tab()
        self.tabs.addTab(self.tab_presets, "Scenarios")

    def _build_target_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(10)
        
        # Target Shape (User-defined, default Square)
        box_shape = QGroupBox("Target Shape & Profile")
        l_shape = QVBoxLayout(box_shape)
        self.combo_shape = QComboBox()
        for shape in TargetShape:
            self.combo_shape.addItem(shape.value, shape)
        self.combo_shape.setCurrentText(self.tracker.primary_target.shape.value)
        self.combo_shape.currentIndexChanged.connect(self._on_shape_changed)
        l_shape.addWidget(QLabel("Target Shape (Default: Square):"))
        l_shape.addWidget(self.combo_shape)
        
        # Target Size (5-20 pixels)
        l_size = QHBoxLayout()
        self.lbl_size = QLabel(f"Size: {self.tracker.primary_target.size}x{self.tracker.primary_target.size} px")
        self.slider_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_size.setRange(5, 20)
        self.slider_size.setValue(self.tracker.primary_target.size)
        self.slider_size.valueChanged.connect(self._on_size_changed)
        l_size.addWidget(self.lbl_size)
        l_size.addWidget(self.slider_size)
        l_shape.addLayout(l_size)
        layout.addWidget(box_shape)
        
        # Motion Trajectory
        box_motion = QGroupBox("Motion Trajectory")
        l_motion = QVBoxLayout(box_motion)
        self.combo_traj = QComboBox()
        for traj in MotionTrajectory:
            self.combo_traj.addItem(traj.value, traj)
        self.combo_traj.setCurrentText(self.tracker.primary_target.trajectory.value)
        self.combo_traj.currentIndexChanged.connect(self._on_traj_changed)
        l_motion.addWidget(QLabel("Trajectory Pattern:"))
        l_motion.addWidget(self.combo_traj)
        
        # Target Speed
        l_spd = QHBoxLayout()
        self.lbl_spd = QLabel(f"Speed: {self.tracker.primary_target.speed:.0f} px/s")
        self.slider_spd = QSlider(Qt.Orientation.Horizontal)
        self.slider_spd.setRange(10, 150)
        self.slider_spd.setValue(int(self.tracker.primary_target.speed))
        self.slider_spd.valueChanged.connect(self._on_speed_changed)
        l_spd.addWidget(self.lbl_spd)
        l_spd.addWidget(self.slider_spd)
        l_motion.addLayout(l_spd)
        layout.addWidget(box_motion)
        
        # Interactive Target Repositioning
        box_actions = QGroupBox("Target Position Controls")
        l_act = QVBoxLayout(box_actions)
        
        btn_center_tgt = QPushButton("Center Beacon at (1000, 1000)")
        btn_center_tgt.clicked.connect(lambda: self.tracker.primary_target.reset_position(1000.0, 1000.0))
        l_act.addWidget(btn_center_tgt)
        
        btn_jump = QPushButton("Simulate Target Jump (Re-acq Test)")
        btn_jump.clicked.connect(self._on_jump_target)
        l_act.addWidget(btn_jump)
        layout.addWidget(box_actions)
        
        layout.addStretch()
        return w

    def _build_optics_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(10)
        
        # Tracking Algorithm Selector
        box_algo = QGroupBox("Computer Vision Algorithm")
        l_algo = QVBoxLayout(box_algo)
        self.combo_algo = QComboBox()
        for algo in TrackingAlgorithm:
            self.combo_algo.addItem(algo.value, algo)
        self.combo_algo.setCurrentText(self.tracker.detector.config.algorithm.value)
        self.combo_algo.currentIndexChanged.connect(self._on_algo_changed)
        l_algo.addWidget(QLabel("Centroiding & Track Method:"))
        l_algo.addWidget(self.combo_algo)
        layout.addWidget(box_algo)

        # AI Deep Learning Settings
        box_ai = QGroupBox("ONNX Detector (Experimental)")
        l_ai = QVBoxLayout(box_ai)
        self.chk_ai_decoy = QCheckBox("Enable Spatial Eccentricity Decoy Filter")
        self.chk_ai_decoy.setChecked(self.tracker.detector.config.enable_ai_decoy_filter)
        self.chk_ai_decoy.toggled.connect(lambda v: setattr(self.tracker.detector.config, "enable_ai_decoy_filter", v))
        l_ai.addWidget(self.chk_ai_decoy)

        l_conf = QHBoxLayout()
        self.lbl_conf = QLabel(f"Response threshold: {self.tracker.detector.config.ai_confidence_threshold:.2f}")
        self.slider_conf = QSlider(Qt.Orientation.Horizontal)
        self.slider_conf.setRange(10, 90)
        self.slider_conf.setValue(int(self.tracker.detector.config.ai_confidence_threshold * 100))
        def _on_ai_conf_changed(val):
            self.tracker.detector.config.ai_confidence_threshold = val / 100.0
            self.lbl_conf.setText(f"Response threshold: {val / 100:.2f}")
        self.slider_conf.valueChanged.connect(_on_ai_conf_changed)
        l_conf.addWidget(self.lbl_conf)
        l_conf.addWidget(self.slider_conf)
        l_ai.addLayout(l_conf)
        layout.addWidget(box_ai)
        
        # Dynamic Track Gate
        box_gate = QGroupBox("Dynamic Track Gate")
        l_gate = QVBoxLayout(box_gate)
        self.chk_gate = QCheckBox("Enable Innovation Track Gate")
        self.chk_gate.setChecked(self.tracker.detector.config.enable_track_gate)
        self.chk_gate.toggled.connect(lambda v: setattr(self.tracker.detector.config, "enable_track_gate", v))
        l_gate.addWidget(self.chk_gate)
        
        l_gsz = QHBoxLayout()
        self.lbl_gate_sz = QLabel(f"Gate Size: {self.tracker.detector.config.gate_size_px} px")
        self.slider_gate_sz = QSlider(Qt.Orientation.Horizontal)
        self.slider_gate_sz.setRange(32, 128)
        self.slider_gate_sz.setValue(self.tracker.detector.config.gate_size_px)
        self.slider_gate_sz.valueChanged.connect(self._on_gate_sz_changed)
        l_gsz.addWidget(self.lbl_gate_sz)
        l_gsz.addWidget(self.slider_gate_sz)
        l_gate.addLayout(l_gsz)
        layout.addWidget(box_gate)
        
        # Automatic Gain Control (AGC)
        box_agc = QGroupBox("FPA Automatic Gain Control")
        l_agc = QVBoxLayout(box_agc)
        self.combo_agc = QComboBox()
        for mode in AGCMode:
            self.combo_agc.addItem(mode.value, mode)
        self.combo_agc.setCurrentText(self.tracker.detector.config.agc_mode.value)
        self.combo_agc.currentIndexChanged.connect(self._on_agc_changed)
        l_agc.addWidget(QLabel("Sensor AGC Mode:"))
        l_agc.addWidget(self.combo_agc)
        layout.addWidget(box_agc)
        
        # Clutter & Decoy Spawning
        box_decoy = QGroupBox("Multi-Target & Clutter Rejection")
        l_decoy = QVBoxLayout(box_decoy)
        
        btn_spawn_decoy = QPushButton("Spawn Decoy Spot in FOV")
        btn_spawn_decoy.clicked.connect(self._on_spawn_decoy)
        l_decoy.addWidget(btn_spawn_decoy)
        
        btn_clear_decoys = QPushButton("Clear All Decoys")
        btn_clear_decoys.clicked.connect(self.tracker.clear_decoys)
        l_decoy.addWidget(btn_clear_decoys)

        self.chk_codelock = QCheckBox("Require temporal CodeLock identity")
        self.code_pattern = QLineEdit(self.tracker.detector.config.code_lock_pattern or "1011001")
        self.code_pattern.setPlaceholderText("Binary pattern, at least 7 symbols")
        self.chk_codelock.setChecked(bool(self.tracker.detector.config.code_lock_pattern))
        self.chk_codelock.toggled.connect(self._on_codelock_changed)
        self.code_pattern.editingFinished.connect(self._on_codelock_changed)
        l_decoy.addWidget(self.chk_codelock)
        l_decoy.addWidget(self.code_pattern)
        layout.addWidget(box_decoy)
        
        layout.addStretch()
        return w

    def _build_camera_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(10)
        
        # Pan/Tilt Motion Constraints (5-10 °/s, default 5 °/s)
        box_gimbal = QGroupBox("Gimbal Speed Constraints (5-10 °/s)")
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
        box_ctrl = QGroupBox("Autonomous Control Law")
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

        # Independent propagation effects.  These remain separate from bulk
        # fog/haze attenuation so evaluators can run meaningful ablations.
        box_turb = QGroupBox("Turbulence, Scintillation & Flicker")
        l_turb = QGridLayout(box_turb)

        def disturbance_spin(value, low, high, step, decimals, suffix, attribute):
            control = QDoubleSpinBox()
            control.setRange(low, high)
            control.setSingleStep(step)
            control.setDecimals(decimals)
            control.setSuffix(suffix)
            control.setValue(value)
            control.valueChanged.connect(
                lambda new_value, attr=attribute: setattr(
                    self.tracker.disturb_config, attr, float(new_value)
                )
            )
            return control

        disturbance = self.tracker.disturb_config
        self.spin_turbulence_warp = disturbance_spin(
            disturbance.turbulence_warp_px, 0.0, 50.0, 0.1, 1, " px", "turbulence_warp_px"
        )
        self.spin_turbulence_blur = disturbance_spin(
            disturbance.turbulence_blur_sigma_px, 0.0, 20.0, 0.1, 1, " px", "turbulence_blur_sigma_px"
        )
        self.spin_scintillation = disturbance_spin(
            disturbance.scintillation_log_std, 0.0, 1.5, 0.01, 2, " σ", "scintillation_log_std"
        )
        self.spin_illumination = disturbance_spin(
            disturbance.illumination_flicker_fraction, 0.0, 0.95, 0.01, 2, "", "illumination_flicker_fraction"
        )
        self.spin_illumination_hz = disturbance_spin(
            disturbance.illumination_flicker_hz, 0.0, 100.0, 0.5, 1, " Hz", "illumination_flicker_hz"
        )
        for row, (label, control) in enumerate((
            ("Angle-of-arrival warp:", self.spin_turbulence_warp),
            ("Seeing blur σ:", self.spin_turbulence_blur),
            ("Scintillation log σ:", self.spin_scintillation),
            ("Illumination depth:", self.spin_illumination),
            ("Illumination frequency:", self.spin_illumination_hz),
        )):
            l_turb.addWidget(QLabel(label), row, 0)
            l_turb.addWidget(control, row, 1)
        layout.addWidget(box_turb)
        
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
        l_noise.addWidget(QLabel("Deterministic random seed:"))
        self.seed_input = QSpinBox()
        self.seed_input.setRange(0, 2_147_483_647)
        self.seed_input.setValue(self.tracker.disturb_config.random_seed)
        self.seed_input.editingFinished.connect(
            lambda: self._on_seed_changed(self.seed_input.value())
        )
        l_noise.addWidget(self.seed_input)
        layout.addWidget(box_noise)
        
        # 3. Camera Jitter (+-20 px)
        box_jit = QGroupBox("Camera Jitter (+-20 px max)")
        l_jit = QVBoxLayout(box_jit)
        self.chk_jit = QCheckBox("Enable High-Frequency Jitter")
        self.chk_jit.toggled.connect(lambda v: setattr(self.tracker.disturb_config, "enable_camera_jitter", v))
        l_jit.addWidget(self.chk_jit)
        layout.addWidget(box_jit)
        
        # 4. Platform Motion (+-20 px)
        box_plat = QGroupBox("Platform Motion (+-20 px max)")
        l_plat = QVBoxLayout(box_plat)
        self.chk_plat = QCheckBox("Enable Platform Motion")
        self.chk_plat.toggled.connect(lambda v: setattr(self.tracker.disturb_config, "enable_platform_motion", v))
        l_plat.addWidget(self.chk_plat)
        
        self.combo_plat = QComboBox()
        for ptype in PlatformMotionType:
            self.combo_plat.addItem(ptype.value, ptype)
        self.combo_plat.currentIndexChanged.connect(self._on_plat_type_changed)
        l_plat.addWidget(self.combo_plat)
        layout.addWidget(box_plat)
        
        layout.addStretch()
        return w

    def _build_presets_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(10)
        
        box_p = QGroupBox("Aerospace Mission Presets")
        l_p = QVBoxLayout(box_p)
        
        presets = [
            ("Nominal Clear Sky (LEO Optical Pass)", "nominal_leo.json"),
            ("Platform Vibration Shock", "platform_jitter.json"),
            ("Heavy Atmospheric Turbulence", "heavy_turbulence.json"),
            ("Cloud Dropout & Re-acquisition", "cloud_dropout.json"),
            ("High Speed Evasive Maneuvers", "evasive_target.json")
        ]
        
        for name, filename in presets:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, fn=filename: self.preset_selected_signal.emit(fn))
            l_p.addWidget(btn)
        layout.addWidget(box_p)
        
        # Telemetry Logging to CSV
        box_log = QGroupBox("Flight Data Recorder (CSV)")
        l_log = QVBoxLayout(box_log)
        self.btn_log = QPushButton("Start Recording Telemetry")
        self.btn_log.setCheckable(True)
        self.btn_log.toggled.connect(self._on_log_toggled)
        l_log.addWidget(self.btn_log)
        self.lbl_log_status = QLabel("Recorder: IDLE")
        l_log.addWidget(self.lbl_log_status)
        layout.addWidget(box_log)
        
        layout.addStretch()
        return w

    def _on_shape_changed(self, idx: int):
        shape = self.combo_shape.currentData()
        self.tracker.primary_target.shape = shape

    def _on_size_changed(self, val: int):
        self.lbl_size.setText(f"Size: {val}x{val} px")
        self.tracker.primary_target.size = val

    def _on_traj_changed(self, idx: int):
        traj = self.combo_traj.currentData()
        self.tracker.primary_target.trajectory = traj
        self.tracker.primary_target.reset_position(self.tracker.primary_target.x, self.tracker.primary_target.y)

    def _on_speed_changed(self, val: int):
        self.lbl_spd.setText(f"Speed: {val} px/s")
        self.tracker.primary_target.speed = float(val)

    def _on_jump_target(self):
        # Displace target by 120px to test re-acquisition
        self.tracker.primary_target.x += 120.0
        self.tracker.primary_target.y += 80.0

    def _on_algo_changed(self, idx: int):
        algo = self.combo_algo.currentData()
        self.tracker.set_algorithm(algo)

    def _on_gate_sz_changed(self, val: int):
        self.lbl_gate_sz.setText(f"Gate Size: {val} px")
        self.tracker.detector.config.gate_size_px = val

    def _on_agc_changed(self, idx: int):
        mode = self.combo_agc.currentData()
        self.tracker.set_agc_mode(mode)

    def _on_spawn_decoy(self):
        # Spawn decoy near camera boresight with slight offset
        cam_x, cam_y = self.tracker.camera.world_x, self.tracker.camera.world_y
        offset_x = self.tracker.disturbances.rng.uniform(-100, 100)
        offset_y = self.tracker.disturbances.rng.uniform(-100, 100)
        self.tracker.spawn_decoy(cam_x + offset_x, cam_y + offset_y, speed=40.0)

    def _on_codelock_changed(self, *_):
        pattern = self.code_pattern.text().strip()
        if self.chk_codelock.isChecked() and len(pattern) >= 7 and set(pattern) == {"0", "1"}:
            self.code_pattern.setStyleSheet("")
            self.tracker.detector.config.code_lock_pattern = pattern
            self.tracker.det_config.code_lock_pattern = pattern
            self.tracker.code_lock = self.tracker._create_codelock()
        elif self.chk_codelock.isChecked():
            self.code_pattern.setStyleSheet("border: 1px solid #dc2626;")
        else:
            self.code_pattern.setStyleSheet("")
            self.tracker.detector.config.code_lock_pattern = None
            self.tracker.det_config.code_lock_pattern = None
            self.tracker.code_lock = None

    def _on_seed_changed(self, value: int):
        self.tracker.configure_random_seed(value)
        self.reset_tracking_signal.emit()

    def _on_pan_spd_changed(self, val: int):
        spd = val / 10.0
        self.lbl_pan_spd.setText(f"Max Pan Speed: {spd:.1f} °/s")
        self.tracker.camera.set_rate_limits(pan_deg_s=spd)

    def _on_tilt_spd_changed(self, val: int):
        spd = val / 10.0
        self.lbl_tilt_spd.setText(f"Max Tilt Speed: {spd:.1f} °/s")
        self.tracker.camera.set_rate_limits(tilt_deg_s=spd)

    def refresh_from_tracker(self):
        """Synchronize visible controls after loading a mission preset."""
        target = self.tracker.primary_target
        disturbance = self.tracker.disturb_config
        self.combo_shape.setCurrentText(target.shape.value)
        self.slider_size.setValue(target.size)
        self.combo_traj.setCurrentText(target.trajectory.value)
        self.slider_spd.setValue(int(target.speed))
        self.slider_pan_spd.setValue(round(self.tracker.cam_config.max_pan_speed_deg_s * 10))
        self.slider_tilt_spd.setValue(round(self.tracker.cam_config.max_tilt_speed_deg_s * 10))
        self.combo_atm.setCurrentText(disturbance.atmospheric_condition.value)
        self.slider_sev.setValue(round(disturbance.atmospheric_severity * 100))
        self.spin_turbulence_warp.setValue(disturbance.turbulence_warp_px)
        self.spin_turbulence_blur.setValue(disturbance.turbulence_blur_sigma_px)
        self.spin_scintillation.setValue(disturbance.scintillation_log_std)
        self.spin_illumination.setValue(disturbance.illumination_flicker_fraction)
        self.spin_illumination_hz.setValue(disturbance.illumination_flicker_hz)
        self.chk_sp.setChecked(disturbance.enable_salt_pepper)
        self.chk_gauss.setChecked(disturbance.enable_gaussian_noise)
        self.chk_poisson.setChecked(disturbance.enable_poisson_noise)
        self.chk_jit.setChecked(disturbance.enable_camera_jitter)
        self.chk_plat.setChecked(disturbance.enable_platform_motion)
        self.combo_plat.setCurrentText(disturbance.platform_motion_type.value)
        self.seed_input.setValue(disturbance.random_seed)
        self.chk_codelock.setChecked(bool(self.tracker.detector.config.code_lock_pattern))
        if self.tracker.detector.config.code_lock_pattern:
            self.code_pattern.setText(self.tracker.detector.config.code_lock_pattern)

    def _on_auto_toggled(self, checked: bool):
        self.tracker.is_autonomous_tracking = checked
        self.toggle_autonomous_signal.emit(checked)

    def _manual_nudge(self, d_pan: float, d_tilt: float):
        self.tracker.camera.apply_pan_tilt_command(d_pan * 5.0, d_tilt * 5.0, 0.1)

    def _on_atm_changed(self, idx: int):
        cond = self.combo_atm.currentData()
        self.tracker.disturb_config.atmospheric_condition = cond

    def _on_atm_sev_changed(self, val: int):
        self.lbl_sev.setText(f"Severity: {val}%")
        self.tracker.disturb_config.atmospheric_severity = val / 100.0

    def _on_plat_type_changed(self, idx: int):
        ptype = self.combo_plat.currentData()
        self.tracker.disturb_config.platform_motion_type = ptype

    def _on_log_toggled(self, checked: bool):
        if checked:
            fn, _ = QFileDialog.getSaveFileName(self, "Export Telemetry CSV", "archis_telemetry.csv", "CSV Files (*.csv)")
            if fn:
                self.start_log_signal.emit(fn)
                self.btn_log.setText("Stop Recording")
                self.lbl_log_status.setText("Recorder: RECORDING (Live CSV)")
            else:
                self.btn_log.setChecked(False)
        else:
            self.stop_log_signal.emit()
            self.btn_log.setText("Start Recording Telemetry")
            self.lbl_log_status.setText("Recorder: SAVED & CLOSED")
