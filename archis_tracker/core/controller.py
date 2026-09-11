"""
Archis Optical Tracker - Autonomous Gimbal Camera Controller
Closed-loop PID controller with feedforward, rate limiting, and autonomous re-acquisition spiral.
"""
import numpy as np
from typing import Tuple, Optional
from .config import ControllerConfig, CameraConfig


class GimbalController:
    def __init__(self, ctrl_config: Optional[ControllerConfig] = None,
                 cam_config: Optional[CameraConfig] = None):
        self.config = ctrl_config or ControllerConfig()
        self.cam_config = cam_config or CameraConfig()
        
        # PID Error Integrals and Previous Errors
        self.integral_pan: float = 0.0
        self.integral_tilt: float = 0.0
        self.prev_error_pan: float = 0.0
        self.prev_error_tilt: float = 0.0
        
        # Spiral search state for autonomous re-acquisition
        self.search_time: float = 0.0
        self.search_origin_pan: float = 0.0
        self.search_origin_tilt: float = 0.0

    def reset(self):
        self.integral_pan = 0.0
        self.integral_tilt = 0.0
        self.prev_error_pan = 0.0
        self.prev_error_tilt = 0.0
        self.search_time = 0.0

    def start_search(self, current_pan: float, current_tilt: float):
        """Initializes spiral search centered at the last known pan/tilt position."""
        self.search_time = 0.0
        self.search_origin_pan = current_pan
        self.search_origin_tilt = current_tilt

    def compute_tracking_command(self, target_vx: float, target_vy: float,
                                 feedforward_vx: float, feedforward_vy: float,
                                 dt: float) -> Tuple[float, float]:
        """
        Computes pan and tilt angular rate commands (deg/s) using closed-loop PID
        to drive the target to the optical boresight center (320, 240).
        """
        center_x = self.cam_config.center_x  # 320.0
        center_y = self.cam_config.center_y  # 240.0
        
        # Pixel error from boresight
        err_x = target_vx - center_x
        err_y = target_vy - center_y
        
        # Deadband
        if abs(err_x) < self.config.deadband_px:
            err_x = 0.0
        if abs(err_y) < self.config.deadband_px:
            err_y = 0.0
            
        # Convert pixel error to angular error (degrees)
        # Pan: +err_x (target to right) requires +pan to center target
        deg_err_pan = err_x / self.cam_config.pixels_per_deg_x
        # Tilt: +err_y (target below center) requires +tilt to center target
        deg_err_tilt = err_y / self.cam_config.pixels_per_deg_y
        
        # Update integrals with anti-windup clamping
        limit = self.config.anti_windup_limit
        self.integral_pan = float(np.clip(self.integral_pan + deg_err_pan * dt, -limit, limit))
        self.integral_tilt = float(np.clip(self.integral_tilt + deg_err_tilt * dt, -limit, limit))
        
        # Derivatives
        deriv_x = (err_x - self.prev_error_pan * self.cam_config.pixels_per_deg_x) / max(1e-4, dt)
        deriv_y = (err_y - self.prev_error_tilt * self.cam_config.pixels_per_deg_y) / max(1e-4, dt)
        self.prev_error_pan = deg_err_pan
        self.prev_error_tilt = deg_err_tilt
        
        # Feedback PID (in degrees/s)
        # Kp * err_x / px_per_deg_x gives slew rate to eliminate position error
        kp = 6.0
        ki = 0.8
        kd = 0.25
        
        u_fb_pan = (kp * err_x + ki * self.integral_pan * self.cam_config.pixels_per_deg_x + kd * deriv_x) / self.cam_config.pixels_per_deg_x
        u_fb_tilt = (kp * err_y + ki * self.integral_tilt * self.cam_config.pixels_per_deg_y + kd * deriv_y) / self.cam_config.pixels_per_deg_y
        
        # Feedforward from target world velocity estimate
        ff_pan = feedforward_vx / self.cam_config.pixels_per_deg_x
        ff_tilt = feedforward_vy / self.cam_config.pixels_per_deg_y
        
        cmd_pan = u_fb_pan + ff_pan
        cmd_tilt = u_fb_tilt + ff_tilt
        
        return float(cmd_pan), float(cmd_tilt)

    def compute_search_command(self, dt: float) -> Tuple[float, float]:
        """
        Computes spiral velocity commands for rapid autonomous re-acquisition (<= 1 sec).
        Expands Archimedean spiral trajectory around the last known target coordinates.
        """
        self.search_time += dt
        t = self.search_time
        
        speed = self.config.search_spiral_speed
        w = 4.0  # Angular scan frequency (rad/s)
        r = min(1.8, 0.4 * t)  # Radius expansion rate (degrees)
        
        # Spiral velocity vector
        cmd_pan = -r * w * np.sin(w * t) + 0.4 * np.cos(w * t)
        cmd_tilt = r * w * np.cos(w * t) + 0.4 * np.sin(w * t)
        
        # Normalize to search speed
        mag = np.hypot(cmd_pan, cmd_tilt)
        if mag > 1e-4:
            cmd_pan = (cmd_pan / mag) * speed
            cmd_tilt = (cmd_tilt / mag) * speed
            
        return float(cmd_pan), float(cmd_tilt)
