"""
Archis Optical Tracker - Virtual Pan-Tilt Camera
Controls the movable virtual camera viewport (640x480) with pan/tilt motion constraints.
"""
import numpy as np
from typing import Tuple, Optional
from .config import CameraConfig, EnvironmentConfig
from .gimbal import GimbalPedestal


class VirtualCamera:
    def __init__(self, cam_config: Optional[CameraConfig] = None, 
                 env_config: Optional[EnvironmentConfig] = None):
        self.config = cam_config or CameraConfig()
        self.env_config = env_config or EnvironmentConfig()
        
        # Two-Axis Mechanical Gimbal Assembly
        self.gimbal = GimbalPedestal(
            max_rate_deg_s=self.config.max_pan_speed_deg_s,
            max_accel_deg_s2=self.config.max_acceleration_deg_s2,
            max_tilt_rate_deg_s=self.config.max_tilt_speed_deg_s,
        )
        
        # Viewport dimensions
        self.width = self.config.viewport_width    # 640
        self.height = self.config.viewport_height  # 480
        
        # Center of the virtual world is the initial camera position
        self.origin_x = self.env_config.screen_width / 2.0   # 1000.0
        self.origin_y = self.env_config.screen_height / 2.0  # 1000.0
        
        # Pan and Tilt angles (degrees)
        self.pan_deg: float = 0.0
        self.tilt_deg: float = 0.0
        
        # Slew rates (degrees/second)
        self.pan_velocity_deg_s: float = 0.0
        self.tilt_velocity_deg_s: float = 0.0
        
        # Rate limits per specification (5 - 10 °/s, default 5 °/s)
        self.max_pan_speed_deg_s = self.config.max_pan_speed_deg_s
        self.max_tilt_speed_deg_s = self.config.max_tilt_speed_deg_s
        
        # Current world center position of camera viewport
        self.world_x: float = self.origin_x
        self.world_y: float = self.origin_y
        
        # Additional platform motion & jitter offsets
        self.jitter_offset_x: float = 0.0
        self.jitter_offset_y: float = 0.0
        self.platform_offset_x: float = 0.0
        self.platform_offset_y: float = 0.0

    def set_rate_limits(self, pan_deg_s: Optional[float] = None,
                        tilt_deg_s: Optional[float] = None):
        """Update configuration and the live mechanical rate clamps."""
        if pan_deg_s is not None:
            self.config.max_pan_speed_deg_s = float(pan_deg_s)
        if tilt_deg_s is not None:
            self.config.max_tilt_speed_deg_s = float(tilt_deg_s)
        self.max_pan_speed_deg_s = self.config.max_pan_speed_deg_s
        self.max_tilt_speed_deg_s = self.config.max_tilt_speed_deg_s
        self.gimbal.max_rate = self.max_pan_speed_deg_s
        self.gimbal.max_tilt_rate = self.max_tilt_speed_deg_s

    def reset(self):
        self.gimbal.reset()
        self.pan_deg = 0.0
        self.tilt_deg = 0.0
        self.pan_velocity_deg_s = 0.0
        self.tilt_velocity_deg_s = 0.0
        self.jitter_offset_x = 0.0
        self.jitter_offset_y = 0.0
        self.platform_offset_x = 0.0
        self.platform_offset_y = 0.0
        self.update_world_position()

    def update_world_position(self):
        """
        Converts pan/tilt angles (in degrees) to virtual world coordinate offset.
        Pixel displacement = angle_deg * (viewport_size / FOV_deg)
        """
        px_per_deg_x = self.config.pixels_per_deg_x
        px_per_deg_y = self.config.pixels_per_deg_y
        
        raw_x = self.origin_x + self.pan_deg * px_per_deg_x + self.jitter_offset_x + self.platform_offset_x
        raw_y = self.origin_y + self.tilt_deg * px_per_deg_y + self.jitter_offset_y + self.platform_offset_y
        
        # Enforce virtual space boundaries so viewport doesn't leave the 2000x2000 canvas
        half_w = self.width / 2.0
        half_h = self.height / 2.0

        # Clamp the physical state as well as the rendered viewport.  Without
        # this the gimbal angle can wind up indefinitely at a world boundary.
        min_pan = (half_w - self.origin_x - self.jitter_offset_x - self.platform_offset_x) / px_per_deg_x
        max_pan = (self.env_config.screen_width - half_w - self.origin_x - self.jitter_offset_x - self.platform_offset_x) / px_per_deg_x
        min_tilt = (half_h - self.origin_y - self.jitter_offset_y - self.platform_offset_y) / px_per_deg_y
        max_tilt = (self.env_config.screen_height - half_h - self.origin_y - self.jitter_offset_y - self.platform_offset_y) / px_per_deg_y
        clamped_pan = float(np.clip(self.pan_deg, min_pan, max_pan))
        clamped_tilt = float(np.clip(self.tilt_deg, min_tilt, max_tilt))
        if clamped_pan != self.pan_deg:
            self.pan_velocity_deg_s = self.gimbal.pan_vel_deg_s = 0.0
        if clamped_tilt != self.tilt_deg:
            self.tilt_velocity_deg_s = self.gimbal.tilt_vel_deg_s = 0.0
        self.pan_deg = self.gimbal.pan_angle_deg = clamped_pan
        self.tilt_deg = self.gimbal.tilt_angle_deg = clamped_tilt

        raw_x = self.origin_x + self.pan_deg * px_per_deg_x + self.jitter_offset_x + self.platform_offset_x
        raw_y = self.origin_y + self.tilt_deg * px_per_deg_y + self.jitter_offset_y + self.platform_offset_y
        
        self.world_x = float(np.clip(raw_x, half_w, self.env_config.screen_width - half_w))
        self.world_y = float(np.clip(raw_y, half_h, self.env_config.screen_height - half_h))

    def apply_pan_tilt_command(self, commanded_pan_vel_deg_s: float, 
                               commanded_tilt_vel_deg_s: float, dt: float,
                               fsm_command: Optional[Tuple[float, float]] = None):
        """
        Applies pan/tilt velocity commands clamped strictly to Max Pan/Tilt Speed constraints (5-10 °/s)
        integrated through two-axis gimbal mechanical dynamics.
        """
        pan, tilt = self.gimbal.step(commanded_pan_vel_deg_s, commanded_tilt_vel_deg_s, dt, fsm_command)
        self.pan_deg = pan
        self.tilt_deg = tilt
        self.pan_velocity_deg_s = self.gimbal.pan_vel_deg_s
        self.tilt_velocity_deg_s = self.gimbal.tilt_vel_deg_s
        self.update_world_position()

    def world_to_viewport(self, wx: float, wy: float) -> Tuple[float, float]:
        """Converts global world coordinates (wx, wy) to camera viewport coordinates (vx, vy)."""
        vx = wx - (self.world_x - self.width / 2.0)
        vy = wy - (self.world_y - self.height / 2.0)
        return vx, vy

    def viewport_to_world(self, vx: float, vy: float) -> Tuple[float, float]:
        """Converts camera viewport coordinates (vx, vy) to global world coordinates (wx, wy)."""
        wx = vx + (self.world_x - self.width / 2.0)
        wy = vy + (self.world_y - self.height / 2.0)
        return wx, wy

    def is_point_in_fov(self, wx: float, wy: float, margin: float = 0.0) -> bool:
        """Checks whether a world point is currently inside the camera's FOV."""
        vx, vy = self.world_to_viewport(wx, wy)
        return (-margin <= vx < self.width + margin and -margin <= vy < self.height + margin)
