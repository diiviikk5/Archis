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
        self.derivative_pan: float = 0.0
        self.derivative_tilt: float = 0.0
        self.filtered_feedforward_pan: float = 0.0
        self.filtered_feedforward_tilt: float = 0.0
        
        # Spiral search state for autonomous re-acquisition
        self.search_time: float = 0.0
        self.search_origin_pan: float = 0.0
        self.search_origin_tilt: float = 0.0

    def reset(self):
        self.integral_pan = 0.0
        self.integral_tilt = 0.0
        self.prev_error_pan = 0.0
        self.prev_error_tilt = 0.0
        self.derivative_pan = self.derivative_tilt = 0.0
        self.filtered_feedforward_pan = self.filtered_feedforward_tilt = 0.0
        self.search_time = 0.0

    def start_search(self, current_pan: float, current_tilt: float):
        """Initializes spiral search centered at the last known pan/tilt position."""
        self.search_time = 0.0
        self.search_origin_pan = current_pan
        self.search_origin_tilt = current_tilt

    def compute_tracking_command(self, target_vx: float, target_vy: float,
                                 feedforward_vx: float, feedforward_vy: float,
                                 dt: float, *,
                                 sensor_width_px: Optional[float] = None,
                                 sensor_height_px: Optional[float] = None) -> Tuple[float, float]:
        """
        Computes pan and tilt angular rate commands (deg/s) using closed-loop PID
        to drive the target to the optical boresight center (320, 240).
        """
        width = float(sensor_width_px or self.cam_config.viewport_width)
        height = float(sensor_height_px or self.cam_config.viewport_height)
        center_x = width / 2.0
        center_y = height / 2.0
        pixels_per_deg_x = width / self.cam_config.fov_x_deg
        pixels_per_deg_y = height / self.cam_config.fov_y_deg
        
        # Pixel error from boresight
        err_x = target_vx - center_x
        err_y = target_vy - center_y
        
        # Deadband
        if abs(err_x) < self.config.deadband_px:
            err_x = 0.0
        if abs(err_y) < self.config.deadband_px:
            err_y = 0.0
            
        deg_err_pan = err_x / pixels_per_deg_x
        deg_err_tilt = err_y / pixels_per_deg_y

        # PID gains operate on angular error and all values come from the
        # configuration. Derivative smoothing prevents pixel noise from
        # becoming a rate reversal.
        limit = self.config.anti_windup_limit
        self.integral_pan = float(np.clip(self.integral_pan + deg_err_pan * dt, -limit, limit))
        self.integral_tilt = float(np.clip(self.integral_tilt + deg_err_tilt * dt, -limit, limit))
        
        # Derivatives
        raw_deriv_pan = (deg_err_pan - self.prev_error_pan) / max(1e-4, dt)
        raw_deriv_tilt = (deg_err_tilt - self.prev_error_tilt) / max(1e-4, dt)
        alpha = self.config.derivative_smoothing
        self.derivative_pan = alpha * self.derivative_pan + (1.0 - alpha) * raw_deriv_pan
        self.derivative_tilt = alpha * self.derivative_tilt + (1.0 - alpha) * raw_deriv_tilt
        self.prev_error_pan = deg_err_pan
        self.prev_error_tilt = deg_err_tilt

        u_fb_pan = (
            self.config.kp_pan * deg_err_pan
            + self.config.ki_pan * self.integral_pan
            + self.config.kd_pan * self.derivative_pan
        )
        u_fb_tilt = (
            self.config.kp_tilt * deg_err_tilt
            + self.config.ki_tilt * self.integral_tilt
            + self.config.kd_tilt * self.derivative_tilt
        )
        
        # Feedforward from target world velocity estimate
        ff_pan = float(np.clip(
            feedforward_vx / pixels_per_deg_x,
            -self.config.max_feedforward_rate_deg_s,
            self.config.max_feedforward_rate_deg_s,
        ))
        ff_tilt = float(np.clip(
            feedforward_vy / pixels_per_deg_y,
            -self.config.max_feedforward_rate_deg_s,
            self.config.max_feedforward_rate_deg_s,
        ))
        ff_alpha = self.config.feedforward_smoothing
        self.filtered_feedforward_pan = (1.0 - ff_alpha) * self.filtered_feedforward_pan + ff_alpha * ff_pan
        self.filtered_feedforward_tilt = (1.0 - ff_alpha) * self.filtered_feedforward_tilt + ff_alpha * ff_tilt
        
        cmd_pan = u_fb_pan + self.config.feedforward_gain * self.filtered_feedforward_pan
        cmd_tilt = u_fb_tilt + self.config.feedforward_gain * self.filtered_feedforward_tilt
        
        return (
            float(np.clip(cmd_pan, -self.cam_config.max_pan_speed_deg_s, self.cam_config.max_pan_speed_deg_s)),
            float(np.clip(cmd_tilt, -self.cam_config.max_tilt_speed_deg_s, self.cam_config.max_tilt_speed_deg_s)),
        )

    def compute_search_command(self, dt: float) -> Tuple[float, float]:
        """
        Computes spiral velocity commands for rapid autonomous re-acquisition (<= 1 sec).
        Expands Archimedean spiral trajectory around the last known target coordinates.
        """
        self.search_time += dt
        timeout = max(dt, self.config.search_timeout_s)
        t = self.search_time % timeout
        
        speed = self.config.search_spiral_speed
        w = 4.0  # Angular scan frequency (rad/s)
        radial_rate = max(0.01, self.config.search_spiral_pitch) * w / (2.0 * np.pi)
        r = radial_rate * t
        
        # Spiral velocity vector
        cmd_pan = -r * w * np.sin(w * t) + radial_rate * np.cos(w * t)
        cmd_tilt = r * w * np.cos(w * t) + radial_rate * np.sin(w * t)
        
        # Normalize to search speed
        mag = np.hypot(cmd_pan, cmd_tilt)
        if mag > 1e-4:
            cmd_pan = (cmd_pan / mag) * speed
            cmd_tilt = (cmd_tilt / mag) * speed
            
        return float(cmd_pan), float(cmd_tilt)
