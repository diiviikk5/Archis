"""
Archis Optical Tracker - Two-Axis Aerospace Gimbal Dynamics Engine
Models mechanical pan-tilt pedestal kinematics, torque saturation,
rate gyro sensor feedback, and fine-steering mirror (FSM) jitter rejection.
"""
import numpy as np
from typing import Tuple, Optional


class GimbalPedestal:
    def __init__(self, max_rate_deg_s: float = 5.0, max_accel_deg_s2: float = 25.0,
                 max_tilt_rate_deg_s: Optional[float] = None):
        # Kinematic limits
        self.max_rate = max_rate_deg_s        # Backward-compatible pan rate
        self.max_tilt_rate = max_tilt_rate_deg_s or max_rate_deg_s
        self.max_accel = max_accel_deg_s2    # 25.0 °/s²
        
        # Physical angles (degrees)
        self.pan_angle_deg: float = 0.0
        self.tilt_angle_deg: float = 0.0
        
        # Physical velocities (degrees/second)
        self.pan_vel_deg_s: float = 0.0
        self.tilt_vel_deg_s: float = 0.0
        
        # Encoder quantization (18-bit resolution)
        self.encoder_res_deg = 360.0 / (2**18)  # ~0.00137°
        
        # Rate gyro sensor simulation (bias + noise)
        self.gyro_bias_pan = 0.002
        self.gyro_bias_tilt = -0.0015
        self.gyro_noise_std = 0.005
        
        # Fine Steering Mirror (FSM) piezo deflection for jitter stabilization (degrees)
        self.fsm_pan_deg: float = 0.0
        self.fsm_tilt_deg: float = 0.0

    def reset(self):
        self.pan_angle_deg = 0.0
        self.tilt_angle_deg = 0.0
        self.pan_vel_deg_s = 0.0
        self.tilt_vel_deg_s = 0.0
        self.fsm_pan_deg = 0.0
        self.fsm_tilt_deg = 0.0

    def step(self, commanded_pan_vel: float, commanded_tilt_vel: float, 
             dt: float, fsm_command: Optional[Tuple[float, float]] = None) -> Tuple[float, float]:
        """
        Integrates gimbal mechanical dynamics with torque limits and acceleration saturation.
        """
        # 1. Commanded rate clamping (5-10 °/s specification)
        target_pan_vel = np.clip(commanded_pan_vel, -self.max_rate, self.max_rate)
        target_tilt_vel = np.clip(commanded_tilt_vel, -self.max_tilt_rate, self.max_tilt_rate)
        
        # 2. Acceleration limits (finite motor torque)
        delta_v_pan = target_pan_vel - self.pan_vel_deg_s
        max_dv = self.max_accel * dt
        self.pan_vel_deg_s += np.clip(delta_v_pan, -max_dv, max_dv)
        
        delta_v_tilt = target_tilt_vel - self.tilt_vel_deg_s
        self.tilt_vel_deg_s += np.clip(delta_v_tilt, -max_dv, max_dv)
        
        # 3. Integrate position
        self.pan_angle_deg += self.pan_vel_deg_s * dt
        self.tilt_angle_deg += self.tilt_vel_deg_s * dt
        
        # 4. Update Fine Steering Mirror if commanded
        if fsm_command:
            # FSM has fast response but small throw (+- 0.5 degrees)
            self.fsm_pan_deg = float(np.clip(fsm_command[0], -0.5, 0.5))
            self.fsm_tilt_deg = float(np.clip(fsm_command[1], -0.5, 0.5))
            
        return self.pan_angle_deg, self.tilt_angle_deg

    @property
    def optical_pointing_pan(self) -> float:
        """Net optical line-of-sight pan angle including FSM."""
        return self.pan_angle_deg + self.fsm_pan_deg

    @property
    def optical_pointing_tilt(self) -> float:
        """Net optical line-of-sight tilt angle including FSM."""
        return self.tilt_angle_deg + self.fsm_tilt_deg

    def read_gyro(self) -> Tuple[float, float]:
        """Returns simulated IMU rate gyro measurements (deg/s) with noise and drift."""
        pan_rate = self.pan_vel_deg_s + self.gyro_bias_pan + np.random.normal(0, self.gyro_noise_std)
        tilt_rate = self.tilt_vel_deg_s + self.gyro_bias_tilt + np.random.normal(0, self.gyro_noise_std)
        return float(pan_rate), float(tilt_rate)
