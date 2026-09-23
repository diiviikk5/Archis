"""
Archis Optical Tracker - Disturbances and Noise Simulation
Implements image noise (Salt & Pepper, Gaussian, Poisson), camera jitter (+-20px),
atmospheric disturbances (Clear, Haze, Fog, Rain, Low Light), and platform motion (+-20px).
"""
import numpy as np
import cv2
from typing import Tuple, Optional
from .config import DisturbanceConfig, AtmosphericCondition, PlatformMotionType


class DisturbanceEngine:
    def __init__(self, config: Optional[DisturbanceConfig] = None):
        self.config = config or DisturbanceConfig()
        self.time_elapsed: float = 0.0
        self.rng = np.random.default_rng(self.config.random_seed)
        
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
        self._initialize_rain()

    def update(self, dt: float) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Updates time-dependent disturbances: camera jitter and platform motion.
        Returns:
            ((jitter_x, jitter_y), (platform_x, platform_y)) in pixels per frame.
        """
        self.time_elapsed += dt
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

    def apply_disturbances_to_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Applies atmospheric disturbances and image noise (Salt & Pepper, Gaussian, Poisson)
        to the captured 640x480 focal plane array video frame.
        """
        img = frame.copy().astype(np.float32)
        h, w = img.shape
        
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
