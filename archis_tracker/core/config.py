"""
Archis Optical Tracker - Configuration and Specifications
Specification parameters for the Autonomous Virtual Camera Tracking System.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple, List, Optional


class TargetShape(Enum):
    SQUARE = "Square"
    CIRCLE = "Circle"
    GAUSSIAN = "Gaussian Spot"
    CROSSHAIR = "Crosshair"


class MotionTrajectory(Enum):
    STRAIGHT_LINE = "Straight Line"
    CIRCULAR = "Circular"
    FIGURE_OF_8 = "Figure of 8"
    RANDOM = "Random (Brownian)"
    SPIRAL = "Spiral"
    SINUSOIDAL = "Sinusoidal"


class AtmosphericCondition(Enum):
    CLEAR = "Clear"
    HAZE = "Haze"
    FOG = "Fog"
    RAIN = "Rain"
    LOW_LIGHT = "Low Light"


class PlatformMotionType(Enum):
    NONE = "None"
    LINEAR = "Linear"
    CIRCULAR = "Circular"
    RANDOM = "Random Jitter"
    SPIRAL = "Spiral"
    FIGURE_OF_8 = "Figure of 8"


class TrackingAlgorithm(Enum):
    HYBRID = "Hybrid AI + Classical + CodeLock"
    IWC = "Intensity Weighted Centroid"
    GAUSSIAN_FIT = "2D Gaussian Surface Fit"
    CORRELATION_NCC = "Normalized Cross-Correlation"
    AI_ONNX = "Deep Learning (NanoSpot-Net ONNX)"


class AGCMode(Enum):
    LINEAR = "Linear Standard"
    HISTOGRAM_EQUALIZATION = "Histogram Equalization"
    PLATEAU_EQUALIZATION = "Plateau Equalization"


class TrackingState(Enum):
    IDLE = "IDLE"
    ACQUIRING = "ACQUIRING"
    TRACKING = "LOCKED TRACKING"
    DEAD_RECKONING = "DEAD RECKONING"
    SEARCHING = "SEARCHING (RE-ACQUISITION)"
    LOST = "TARGET LOST"


@dataclass
class CameraConfig:
    # Camera Parameters per specification
    viewport_width: int = 640
    viewport_height: int = 480
    fov_x_deg: float = 4.0
    fov_y_deg: float = 3.0
    update_rate_hz: float = 30.0  # >= 30 Hz
    max_pan_speed_deg_s: float = 5.0   # 5-10 °/s, default 5
    max_tilt_speed_deg_s: float = 5.0  # 5-10 °/s, default 5
    max_acceleration_deg_s2: float = 25.0
    is_monochrome: bool = True
    color_map: str = "gray"  # "gray", "inferno", "viridis"

    @property
    def pixels_per_deg_x(self) -> float:
        return self.viewport_width / self.fov_x_deg

    @property
    def pixels_per_deg_y(self) -> float:
        return self.viewport_height / self.fov_y_deg

    @property
    def center_x(self) -> float:
        return self.viewport_width / 2.0

    @property
    def center_y(self) -> float:
        return self.viewport_height / 2.0


@dataclass
class EnvironmentConfig:
    # Virtual Environment Parameters
    screen_width: int = 2000   # min 2000x2000
    screen_height: int = 2000
    star_count: int = 250
    grid_spacing: int = 100
    background_intensity: int = 12
    random_seed: int = 26169


@dataclass
class TerminalWorldConfig:
    """Physical geometry layered over the legacy angular simulation plane.

    The existing 2000x2000 world remains the deterministic angular scene used
    to render camera pixels.  This configuration gives that plane a physical
    range and an explicit receiving-terminal pose without changing legacy
    presets or detector inputs.
    """

    nominal_range_m: float = 1000.0
    receiver_position_m: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    receiver_velocity_m_s: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    receiver_orientation_deg: Tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class TargetConfig:
    # Target Parameters per specification
    shape: TargetShape = TargetShape.SQUARE
    size: int = 10  # 5-20 pixels, default 10x10
    trajectory: MotionTrajectory = MotionTrajectory.FIGURE_OF_8
    speed: float = 45.0  # pixels / second
    intensity: float = 255.0
    secondary_targets: int = 0  # 1 mandatory, multiple optional
    initial_x: Optional[float] = None
    initial_y: Optional[float] = None
    # Trajectory specific params
    trajectory_radius: float = 350.0
    trajectory_omega: float = 0.25
    random_seed: int = 26169
    # Physical terminal metadata.  Range defaults to the world's nominal
    # range when omitted; orientation is yaw, pitch and roll in degrees.  A
    # missing orientation makes the simulated transmitter face the receiver.
    range_m: Optional[float] = None
    orientation_deg: Optional[Tuple[float, float, float]] = None


@dataclass
class DisturbanceConfig:
    random_seed: int = 26169
    # Noise & Disturbance specifications
    enable_salt_pepper: bool = False
    salt_pepper_ratio: float = 0.05  # up to ~10%
    
    enable_gaussian_noise: bool = False
    gaussian_noise_std: float = 10.0  # max standard deviation 20
    
    enable_poisson_noise: bool = False
    
    enable_camera_jitter: bool = False
    max_camera_jitter_px: float = 8.0  # max +- 20 pixels/frame
    
    atmospheric_condition: AtmosphericCondition = AtmosphericCondition.CLEAR
    atmospheric_severity: float = 0.5  # 0.0 to 1.0 (contrast/brightness reduction)

    # Turbulence is modelled separately from bulk haze/fog attenuation.  The
    # warp represents angle-of-arrival fluctuations, the blur represents
    # seeing, and the log-normal term represents irradiance scintillation.
    turbulence_warp_px: float = 0.0
    turbulence_blur_sigma_px: float = 0.0
    scintillation_log_std: float = 0.0
    # Optional physically parameterised Gamma-Gamma irradiance model.  The
    # legacy log-normal model remains the default for preset compatibility.
    scintillation_model: str = "lognormal"
    rytov_variance: float = 0.0

    # Periodic source/background illumination variation.  A value of 0.15
    # varies the image gain by +/-15 percent around unity.
    illumination_flicker_fraction: float = 0.0
    illumination_flicker_hz: float = 3.0
    
    enable_platform_motion: bool = False
    platform_motion_type: PlatformMotionType = PlatformMotionType.LINEAR
    platform_motion_amplitude_px: float = 5.0  # max +- 20 pixels/frame
    platform_motion_frequency_hz: float = 0.5
    dropout_enabled: bool = False
    dropout_start_s: float = 0.0
    dropout_duration_s: float = 0.0
    # Optional two-state burst-loss channel.  Transition probabilities are
    # derived from these mean dwell times, making the model independent of
    # the configured sensor frame rate while remaining repeatable by seed.
    dropout_burst_enabled: bool = False
    dropout_mean_clear_s: float = 8.0
    dropout_mean_loss_s: float = 0.25


@dataclass
class ControllerConfig:
    # Closed-loop PID and tracking controller gains
    kp_pan: float = 8.0
    ki_pan: float = 0.18
    kd_pan: float = 0.04
    
    kp_tilt: float = 8.0
    ki_tilt: float = 0.18
    kd_tilt: float = 0.04
    
    anti_windup_limit: float = 3.0
    deadband_px: float = 0.5
    derivative_smoothing: float = 0.7
    feedforward_gain: float = 0.8
    feedforward_smoothing: float = 0.1
    max_feedforward_rate_deg_s: float = 4.0
    # Known sensor/processing/actuator delay.  The tracker projects the
    # filtered kinematic state by this horizon before computing the command.
    latency_compensation_s: float = 0.0
    
    # Re-acquisition spiral search
    search_spiral_speed: float = 3.0  # deg/s
    search_spiral_pitch: float = 0.8  # deg/turn
    search_timeout_s: float = 4.0
    coast_timeout_s: float = 0.4
    local_reacquire_timeout_s: float = 0.6
    acquisition_confirmation_frames: int = 3
    periodic_full_scan_frames: int = 30


@dataclass
class PerformanceThresholds:
    # Performance Specifications
    max_acquisition_time_s: float = 2.0
    max_tracking_error_px: float = 10.0
    max_target_loss_pct: float = 5.0
    max_reacquisition_time_s: float = 1.0
    min_processing_fps: float = 20.0


@dataclass
class DetectorConfig:
    algorithm: TrackingAlgorithm = TrackingAlgorithm.HYBRID
    enable_track_gate: bool = True
    gate_size_px: int = 64
    k_sigma_threshold: float = 2.6
    subpixel_precision: bool = True
    min_target_area: int = 4
    max_target_area: int = 450
    enable_scale_relative_geometry: bool = True
    fallback_fwhm_px: float = 8.0
    minimum_fwhm_px: float = 2.0
    maximum_fwhm_px: float = 32.0
    # Rounded conservative p95 fit from the deterministic optical validation
    # matrix (spot FWHM 3/7/15 px, noise sigma 1/6/14, unsaturated peaks).
    measurement_noise_calibration: float = 14.2
    measurement_noise_floor_px: float = 0.15
    measurement_noise_ceiling_px: float = 20.0
    agc_mode: AGCMode = AGCMode.LINEAR
    ai_confidence_threshold: float = 0.88
    enable_ai_decoy_filter: bool = True
    candidate_verifier_threshold: float = 0.35
    code_lock_pattern: Optional[str] = None
    code_lock_symbol_frames: int = 1
    code_lock_minimum_correlation: float = 0.70
    # A deliberately wide second-stage sanity gate protects the estimator
    # from catastrophic jumps without duplicating the detector's stricter
    # 99% candidate-association gate or rejecting aggressive manoeuvres.
    kalman_gate_threshold_chi2: float = 10000.0
