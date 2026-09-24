"""
Archis Optical Tracker - 6-State Extended Kalman Filter (EKF)
Estimates position, velocity, and acceleration in 2D with kinematic prediction.
State vector: x = [pos_x, vel_x, acc_x, pos_y, vel_y, acc_y]^T
"""
import numpy as np
from typing import Tuple, Optional


class KalmanFilter2D:
    def __init__(self, q_accel_noise: float = 8.0, r_measurement_noise: float = 1.5):
        # 6 states: [x, vx, ax, y, vy, ay]
        self.state = np.zeros(6, dtype=np.float32)
        self.cov = np.eye(6, dtype=np.float32) * 50.0  # Initial uncertainty
        
        self.q_noise = q_accel_noise
        self.r_noise = r_measurement_noise
        self.is_initialized: bool = False
        self.last_innovation_distance_sq: Optional[float] = None
        self.last_measurement_accepted: bool = False

    def reset(self, init_x: float = 320.0, init_y: float = 240.0):
        self.state = np.array([init_x, 0.0, 0.0, init_y, 0.0, 0.0], dtype=np.float32)
        self.cov = np.diag([2.0, 20.0, 50.0, 2.0, 20.0, 50.0]).astype(np.float32)
        self.is_initialized = True
        self.last_innovation_distance_sq = None
        self.last_measurement_accepted = False

    def predict(self, dt: float) -> Tuple[float, float]:
        """
        Propagates state and covariance forward by dt using kinematic constant-acceleration model.
        Returns predicted position (x_pred, y_pred).
        """
        if not self.is_initialized:
            return 320.0, 240.0
            
        dt2 = 0.5 * dt * dt
        
        # State transition matrix F
        F = np.eye(6, dtype=np.float32)
        # X channel
        F[0, 1] = dt
        F[0, 2] = dt2
        F[1, 2] = dt
        # Y channel
        F[3, 4] = dt
        F[3, 5] = dt2
        F[4, 5] = dt
        
        # Process noise covariance.  This retains the calibrated discrete
        # acceleration-noise convention used by existing Archis profiles.
        Q = np.zeros((6, 6), dtype=np.float32)
        dt3 = dt * dt2 / 3.0
        dt4 = dt2 * dt2

        q = self.q_noise
        Q[0, 0] = dt4 / 4.0 * q
        Q[0, 1] = dt3 / 2.0 * q
        Q[0, 2] = dt2 / 2.0 * q
        Q[1, 0] = Q[0, 1]
        Q[1, 1] = dt * dt * q
        Q[1, 2] = dt * q
        Q[2, 0] = Q[0, 2]
        Q[2, 1] = Q[1, 2]
        Q[2, 2] = q
        Q[3:6, 3:6] = Q[0:3, 0:3]
        
        # Predict state and covariance
        self.state = F @ self.state
        self.cov = F @ self.cov @ F.T + Q
        
        return float(self.state[0]), float(self.state[3])

    def update(
        self,
        meas_x: float,
        meas_y: float,
        confidence: float = 1.0,
        gate_threshold_chi2: Optional[float] = None,
    ) -> bool:
        """
        Incorporates measurement (meas_x, meas_y) into the state estimate.
        Adaptive R based on detector confidence.  When a chi-square threshold
        is supplied, statistically incompatible measurements are rejected
        before they can corrupt the state.  Returns whether the measurement
        was accepted.
        """
        if not self.is_initialized:
            self.reset(meas_x, meas_y)
            self.last_measurement_accepted = True
            return True

        # Measurement matrix H (observes x and y)
        H = np.zeros((2, 6), dtype=np.float32)
        H[0, 0] = 1.0
        H[1, 3] = 1.0
        
        # Adaptive measurement noise covariance R
        conf = max(0.1, min(1.0, confidence))
        r_eff = self.r_noise / (conf * conf)
        R = np.eye(2, dtype=np.float32) * r_eff
        
        z = np.array([meas_x, meas_y], dtype=np.float32)
        y = z - H @ self.state  # Innovation / residual
        
        S = H @ self.cov @ H.T + R  # Innovation covariance
        try:
            solved_innovation = np.linalg.solve(S, y)
            innovation_distance_sq = float((y.T @ solved_innovation).item())
            K = np.linalg.solve(S, H @ self.cov).T
        except np.linalg.LinAlgError:
            self.last_innovation_distance_sq = float("inf")
            self.last_measurement_accepted = False
            return False

        self.last_innovation_distance_sq = innovation_distance_sq
        if gate_threshold_chi2 is not None and innovation_distance_sq > gate_threshold_chi2:
            self.last_measurement_accepted = False
            return False
        
        # State & covariance update
        self.state = self.state + K @ y
        I = np.eye(6, dtype=np.float32)
        # Joseph form preserves symmetry and positive semi-definiteness under
        # finite precision better than the abbreviated (I-KH)P form.
        I_KH = I - K @ H
        self.cov = I_KH @ self.cov @ I_KH.T + K @ R @ K.T
        self.cov = 0.5 * (self.cov + self.cov.T)
        self.last_measurement_accepted = True
        return True

    def predict_position(self, horizon_s: float) -> Tuple[float, float]:
        """Project the current kinematic estimate without mutating the filter."""
        horizon = max(0.0, float(horizon_s))
        x = self.state[0] + self.state[1] * horizon + 0.5 * self.state[2] * horizon * horizon
        y = self.state[3] + self.state[4] * horizon + 0.5 * self.state[5] * horizon * horizon
        return float(x), float(y)

    @property
    def position(self) -> Tuple[float, float]:
        return float(self.state[0]), float(self.state[3])

    @property
    def velocity(self) -> Tuple[float, float]:
        return float(self.state[1]), float(self.state[4])

    @property
    def acceleration(self) -> Tuple[float, float]:
        return float(self.state[2]), float(self.state[5])

    @property
    def speed(self) -> float:
        return float(np.hypot(self.state[1], self.state[4]))

    @property
    def innovation_covariance(self) -> np.ndarray:
        """Returns 2x2 measurement innovation covariance S = H P H^T + R for gating."""
        H = np.zeros((2, 6), dtype=np.float32)
        H[0, 0] = 1.0
        H[1, 3] = 1.0
        R = np.eye(2, dtype=np.float32) * self.r_noise
        return H @ self.cov @ H.T + R
