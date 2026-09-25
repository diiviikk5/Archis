"""
Archis Optical Tracker - Disturbances and Noise Simulation
Implements image noise (Salt & Pepper, Gaussian, Poisson), camera jitter (+-20px),
atmospheric disturbances (Clear, Haze, Fog, Rain, Low Light), and platform motion (+-20px).
"""
import numpy as np
import cv2
from typing import Tuple, Optional
from .config import DisturbanceConfig, AtmosphericCondition, PlatformMotionType


def gamma_gamma_parameters(rytov_variance: float) -> tuple[float, float]:
    """Return small- and large-scale Gamma-Gamma shape parameters.

    The input is the Rytov variance (not its square root). Values near zero
    approach a deterministic unity gain and are represented by large finite
    shape parameters for stable sampling.
    """
    variance = max(0.0, float(rytov_variance))
    if variance <= 1e-9:
        return 1e9, 1e9
    power = variance ** 1.2
    alpha_term = np.exp(0.49 * variance / (1.0 + 1.11 * power) ** (7.0 / 6.0)) - 1.0
    beta_term = np.exp(0.51 * variance / (1.0 + 0.69 * power) ** (5.0 / 6.0)) - 1.0
    return 1.0 / max(alpha_term, 1e-9), 1.0 / max(beta_term, 1e-9)


def sample_gamma_gamma_gain(rng: np.random.Generator, rytov_variance: float) -> float:
    """Sample unit-mean irradiance gain from a Gamma-Gamma channel."""
    alpha, beta = gamma_gamma_parameters(rytov_variance)
    if alpha >= 1e8 or beta >= 1e8:
        return 1.0
    large_scale = rng.gamma(alpha, 1.0 / alpha)
    small_scale = rng.gamma(beta, 1.0 / beta)
    return float(large_scale * small_scale)


class DisturbanceEngine:
    def __init__(self, config: Optional[DisturbanceConfig] = None):
        self.config = config or DisturbanceConfig()
        self.time_elapsed: float = 0.0
        self.rng = np.random.default_rng(self.config.random_seed)
        self._dropout_rng = np.random.default_rng(self.config.random_seed ^ 0x4C4F5353)
        self._inertial_rng = np.random.default_rng(self.config.random_seed ^ 0x494D5531)
        self._burst_dropout_active = False
        self._coordinate_grids: dict[tuple[int, int], tuple[np.ndarray, np.ndarray]] = {}
        self._turbulence_bases: dict[tuple[int, int], tuple[np.ndarray, ...]] = {}
        phase_rng = np.random.default_rng(self.config.random_seed ^ 0x54555242)
        self._turbulence_phase = phase_rng.uniform(0.0, 2.0 * np.pi, 4)
        
        self._initialize_rain()

    def _initialize_rain(self) -> None:
        """Create the persistent rain field from the session RNG."""
        # Rain streaks persistent state
        self.num_raindrops = 120
        self.rain_x = self.rng.uniform(0, 640, self.num_raindrops).astype(np.float32)
        self.rain_y = self.rng.uniform(0, 480, self.num_raindrops).astype(np.float32)
        self.rain_len = self.rng.uniform(10, 25, self.num_raindrops).astype(np.float32)
        self.rain_speed = self.rng.uniform(350, 600, self.num_raindrops).astype(np.float32)

    def reset(self) -> None:
        self.time_elapsed = 0.0
        self.rng = np.random.default_rng(self.config.random_seed)
        self._dropout_rng = np.random.default_rng(self.config.random_seed ^ 0x4C4F5353)
        self._inertial_rng = np.random.default_rng(self.config.random_seed ^ 0x494D5531)
        self._burst_dropout_active = False
        self._coordinate_grids.clear()
        self._turbulence_bases.clear()
        phase_rng = np.random.default_rng(self.config.random_seed ^ 0x54555242)
        self._turbulence_phase = phase_rng.uniform(0.0, 2.0 * np.pi, 4)
        self._initialize_rain()

    def _grid(self, height: int, width: int) -> tuple[np.ndarray, np.ndarray]:
        """Return cached float32 remap coordinates for a frame size."""
        shape = (height, width)
        if shape not in self._coordinate_grids:
            grid_y, grid_x = np.indices(shape, dtype=np.float32)
            self._coordinate_grids[shape] = grid_x, grid_y
        return self._coordinate_grids[shape]

    def _turbulence_basis(self, height: int, width: int) -> tuple[np.ndarray, ...]:
        """Cache spatial phase terms; each frame then needs only scalar trig."""
        shape = (height, width)
        if shape not in self._turbulence_bases:
            grid_x, grid_y = self._grid(height, width)
            cell = max(8.0, min(height, width) / 18.0)
            phase = self._turbulence_phase
            angles = (
                grid_y / cell + phase[0],
                (grid_x + grid_y) / (1.7 * cell) + phase[1],
                grid_x / cell + phase[2],
                (grid_x - grid_y) / (1.9 * cell) + phase[3],
            )
            self._turbulence_bases[shape] = tuple(
                item.astype(np.float32, copy=False)
                for angle in angles
                for item in (np.sin(angle), np.cos(angle))
            )
        return self._turbulence_bases[shape]

    def update(self, dt: float) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Updates time-dependent disturbances: camera jitter and platform motion.
        Returns:
            ((jitter_x, jitter_y), (platform_x, platform_y)) in pixels per frame.
        """
        self.time_elapsed += dt
        self._update_burst_dropout(dt)
        t = self.time_elapsed
        
        # 1. Camera Jitter (+- 20 pixels / frame max)
        jitter_x, jitter_y = 0.0, 0.0
        if self.config.enable_camera_jitter:
            max_j = min(20.0, self.config.max_camera_jitter_px)
            # High-frequency multi-harmonic jitter + random walk
            jitter_x = (np.sin(2.0 * np.pi * 37.0 * t) * 0.5 + 
                        np.sin(2.0 * np.pi * 63.0 * t) * 0.3 + 
                        self.rng.normal(0, 0.2)) * max_j
            jitter_y = (np.cos(2.0 * np.pi * 41.0 * t) * 0.5 + 
                        np.cos(2.0 * np.pi * 71.0 * t) * 0.3 + 
                        self.rng.normal(0, 0.2)) * max_j
            jitter_x = float(np.clip(jitter_x, -20.0, 20.0))
            jitter_y = float(np.clip(jitter_y, -20.0, 20.0))
            
        # 2. Platform Motion (+- 20 pixels / frame max)
        plat_x, plat_y = 0.0, 0.0
        if self.config.enable_platform_motion:
            amp = min(20.0, self.config.platform_motion_amplitude_px)
            f = self.config.platform_motion_frequency_hz
            ptype = self.config.platform_motion_type
            
            if ptype == PlatformMotionType.LINEAR:
                plat_x = amp * np.sin(2.0 * np.pi * f * t)
                plat_y = amp * 0.5 * np.cos(2.0 * np.pi * f * t)
            elif ptype == PlatformMotionType.CIRCULAR:
                plat_x = amp * np.cos(2.0 * np.pi * f * t)
                plat_y = amp * np.sin(2.0 * np.pi * f * t)
            elif ptype == PlatformMotionType.FIGURE_OF_8:
                plat_x = amp * np.sin(2.0 * np.pi * f * t)
                plat_y = amp * np.sin(4.0 * np.pi * f * t)
            elif ptype == PlatformMotionType.SPIRAL:
                r = (amp * (t % 5.0) / 5.0)
                plat_x = r * np.cos(2.0 * np.pi * f * t)
                plat_y = r * np.sin(2.0 * np.pi * f * t)
            elif ptype == PlatformMotionType.RANDOM:
                plat_x = float(np.clip(self.rng.normal(0, amp * 0.5), -amp, amp))
                plat_y = float(np.clip(self.rng.normal(0, amp * 0.5), -amp, amp))
                
        # 3. Update rain drops
        if self.config.atmospheric_condition == AtmosphericCondition.RAIN:
            self.rain_y += self.rain_speed * dt
            self.rain_x += self.rain_speed * 0.25 * dt  # Angled wind
            wrap = self.rain_y >= 480.0
            self.rain_y[wrap] = 0.0
            self.rain_x[wrap] = self.rng.uniform(0, 640, np.sum(wrap))
            
        return (jitter_x, jitter_y), (plat_x, plat_y)

    def measure_platform_offset(self, actual_x: float, actual_y: float, noise_px: float) -> tuple[float, float]:
        """Simulate a seeded inertial attitude readout independent of beacon truth."""
        sigma = max(0.0, float(noise_px))
        if sigma == 0.0:
            return float(actual_x), float(actual_y)
        noise = self._inertial_rng.normal(0.0, sigma, 2)
        return float(actual_x + noise[0]), float(actual_y + noise[1])

    def _update_burst_dropout(self, dt: float) -> None:
        """Advance a deterministic two-state continuous-time loss process."""
        if not self.config.dropout_burst_enabled:
            self._burst_dropout_active = False
            return
        mean_dwell = (
            self.config.dropout_mean_loss_s
            if self._burst_dropout_active
            else self.config.dropout_mean_clear_s
        )
        mean_dwell = max(1e-6, float(mean_dwell))
        transition_probability = 1.0 - np.exp(-max(0.0, float(dt)) / mean_dwell)
        if self._dropout_rng.random() < transition_probability:
            self._burst_dropout_active = not self._burst_dropout_active

    def is_dropout_active(self) -> bool:
        """Return scheduled or burst signal-loss state for the current frame."""
        scheduled = (
            self.config.dropout_enabled
            and self.config.dropout_start_s <= self.time_elapsed
            < self.config.dropout_start_s + self.config.dropout_duration_s
        )
        return bool(scheduled or self._burst_dropout_active)

    def apply_disturbances_to_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Applies atmospheric disturbances and image noise (Salt & Pepper, Gaussian, Poisson)
        to the captured 640x480 focal plane array video frame.
        """
        img = frame.copy().astype(np.float32)
        h, w = img.shape

        # Illumination flicker is applied before atmospheric propagation.  It
        # is deterministic for a fixed time step and does not consume RNG.
        flicker_depth = float(np.clip(self.config.illumination_flicker_fraction, 0.0, 0.95))
        if flicker_depth > 0.0:
            flicker = 1.0 + flicker_depth * np.sin(
                2.0 * np.pi * max(0.0, self.config.illumination_flicker_hz) * self.time_elapsed
            )
            img *= max(0.05, flicker)
        
        # 1. Atmospheric Disturbance
        atm = self.config.atmospheric_condition
        sev = self.config.atmospheric_severity
        
        if atm == AtmosphericCondition.CLEAR:
            pass  # Nominal baseline
            
        elif atm == AtmosphericCondition.HAZE:
            # Contrast reduction and light veil
            veil = 35.0 * sev
            img = img * (1.0 - 0.45 * sev) + veil
            
        elif atm == AtmosphericCondition.FOG:
            # Heavy Mie scatter blur + strong contrast attenuation
            ksize = int(3 + int(sev * 4) * 2)  # 3, 5, 7, 9
            img = cv2.GaussianBlur(img, (ksize, ksize), sigmaX=ksize/2.0)
            fog_veil = 70.0 * sev
            img = img * (1.0 - 0.70 * sev) + fog_veil
            
        elif atm == AtmosphericCondition.RAIN:
            # Contrast reduction + dynamic rain streaks
            img = img * (1.0 - 0.25 * sev)
            for rx, ry, rlen in zip(self.rain_x, self.rain_y, self.rain_len):
                x1, y1 = int(rx), int(ry)
                x2, y2 = int(rx + rlen * 0.25), int(ry + rlen)
                if 0 <= x1 < w and 0 <= y1 < h:
                    cv2.line(img, (x1, y1), (min(w-1, x2), min(h-1, y2)), 
                             (float(min(255.0, 180.0 * sev))), 1)
                             
        elif atm == AtmosphericCondition.LOW_LIGHT:
            # Heavy reduction in brightness and SNR
            factor = max(0.15, 1.0 - 0.75 * sev)
            img = img * factor

        # Atmospheric turbulence: deterministic moving phase screens for
        # angle-of-arrival distortion, optional seeing blur, and a log-normal
        # scintillation multiplier whose mean is one.  Keeping these controls
        # independent makes ablation and stress-envelope runs meaningful.
        warp_px = max(0.0, float(self.config.turbulence_warp_px))
        if warp_px > 0.0:
            grid_x, grid_y = self._grid(h, w)
            t = self.time_elapsed
            sin_a, cos_a, sin_b, cos_b, sin_c, cos_c, sin_d, cos_d = self._turbulence_basis(h, w)
            # Compose the same cached phase screens in OpenCV's float32 SIMD
            # kernels. NumPy's chained expression allocated a dozen full-size
            # temporary arrays for every frame and dominated turbulent runs.
            dx = cv2.addWeighted(
                sin_a, 0.65 * warp_px * np.cos(4.1 * t),
                cos_a, 0.65 * warp_px * np.sin(4.1 * t), 0.0,
            )
            dx_secondary = cv2.addWeighted(
                sin_b, 0.35 * warp_px * np.cos(2.3 * t),
                cos_b, -0.35 * warp_px * np.sin(2.3 * t), 0.0,
            )
            cv2.add(dx, dx_secondary, dst=dx)
            dy = cv2.addWeighted(
                cos_c, 0.65 * warp_px * np.cos(3.7 * t),
                sin_c, -0.65 * warp_px * np.sin(3.7 * t), 0.0,
            )
            dy_secondary = cv2.addWeighted(
                cos_d, 0.35 * warp_px * np.cos(2.9 * t),
                sin_d, -0.35 * warp_px * np.sin(2.9 * t), 0.0,
            )
            cv2.add(dy, dy_secondary, dst=dy)
            map_x = cv2.add(grid_x, dx)
            map_y = cv2.add(grid_y, dy)
            img = cv2.remap(
                img, map_x, map_y,
                cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101,
            )

        blur_sigma = max(0.0, float(self.config.turbulence_blur_sigma_px))
        if blur_sigma > 0.0:
            img = cv2.GaussianBlur(img, (0, 0), sigmaX=blur_sigma, sigmaY=blur_sigma)

        scintillation = float(np.clip(self.config.scintillation_log_std, 0.0, 1.5))
        if self.config.scintillation_model == "gamma_gamma" and self.config.rytov_variance > 0.0:
            img *= sample_gamma_gamma_gain(self.rng, self.config.rytov_variance)
        elif scintillation > 0.0:
            # exp(N(-sigma^2/2, sigma)) is log-normal with E[gain] = 1.
            gain = np.exp(self.rng.normal(-0.5 * scintillation**2, scintillation))
            img *= float(gain)

        # 2. Salt & Pepper Noise (around 10% of image, user selectable)
        if self.config.enable_salt_pepper:
            ratio = min(0.15, max(0.01, self.config.salt_pepper_ratio))
            num_sp = int(ratio * h * w)
            # Salt
            sp_y = self.rng.integers(0, h, num_sp // 2)
            sp_x = self.rng.integers(0, w, num_sp // 2)
            img[sp_y, sp_x] = 255.0
            # Pepper
            sp_y = self.rng.integers(0, h, num_sp // 2)
            sp_x = self.rng.integers(0, w, num_sp // 2)
            img[sp_y, sp_x] = 0.0

        # 3. Gaussian Noise (Standard deviation up to 20 pixels / intensity)
        if self.config.enable_gaussian_noise:
            std = min(20.0, max(1.0, self.config.gaussian_noise_std))
            gauss = self.rng.normal(0.0, std, (h, w)).astype(np.float32)
            img = img + gauss

        # 4. Poisson Shot Noise
        if self.config.enable_poisson_noise:
            # Scaled Poisson noise
            norm_img = np.clip(img / 255.0, 0.0, 1.0)
            vals = len(np.unique(norm_img))
            vals = 2 ** np.ceil(np.log2(vals))
            noisy = self.rng.poisson(norm_img * vals) / float(vals)
            img = noisy * 255.0

        # Final clip to valid 8-bit dynamic range [0, 255]
        return np.clip(img, 0.0, 255.0).astype(np.uint8)
