"""
Archis Optical Tracker - Integrated Tracking System Engine
Coordinates Environment, Target, Camera, Disturbances, Detector, Kalman Filter, Controller, and Telemetry.
"""
import numpy as np
import time
from typing import Tuple, List, Optional
from .config import (CameraConfig, EnvironmentConfig, TargetConfig, 
                     DisturbanceConfig, ControllerConfig, TrackingState)
from .environment import VirtualEnvironment
from .target import TargetBeacon
from .camera import VirtualCamera
from .disturbances import DisturbanceEngine
from .detector import BeaconDetector, DetectionResult
from .kalman_filter import KalmanFilter2D
from .controller import GimbalController
from .telemetry import TelemetryEngine


class TrackingSystem:
    def __init__(self, cam_config: Optional[CameraConfig] = None,
                 env_config: Optional[EnvironmentConfig] = None,
                 target_config: Optional[TargetConfig] = None,
                 disturb_config: Optional[DisturbanceConfig] = None,
                 ctrl_config: Optional[ControllerConfig] = None):
                 
        self.cam_config = cam_config or CameraConfig()
        self.env_config = env_config or EnvironmentConfig()
        self.target_config = target_config or TargetConfig()
        self.disturb_config = disturb_config or DisturbanceConfig()
        self.ctrl_config = ctrl_config or ControllerConfig()
        
        # Sub-systems
        self.environment = VirtualEnvironment(self.env_config)
        self.camera = VirtualCamera(self.cam_config, self.env_config)
        self.disturbances = DisturbanceEngine(self.disturb_config)
        self.detector = BeaconDetector()
        self.kalman = KalmanFilter2D()
        self.controller = GimbalController(self.ctrl_config, self.cam_config)
        self.telemetry = TelemetryEngine()
        
        # Primary target
        self.primary_target = TargetBeacon(0, self.target_config, is_primary=True)
        # Secondary decoy targets (optional)
        self.secondary_targets: List[TargetBeacon] = []
        
        # Tracking State Machine
        self.state: TrackingState = TrackingState.ACQUIRING
        self.state_timer: float = 0.0
        self.sim_time: float = 0.0
        
        # Last known visual frame and detection
        self.current_frame: np.ndarray = np.zeros((480, 640), dtype=np.uint8)
        self.last_detection: DetectionResult = DetectionResult(detected=False)
        self.latest_pred_x: float = 320.0
        self.latest_pred_y: float = 240.0
        
        # Closed-loop tracking autonomous toggle
        self.is_autonomous_tracking: bool = True

    def reset(self):
        """Resets the entire system to initial baseline parameters."""
        self.camera.reset()
        self.primary_target.reset_position(1000.0, 1000.0)
        self.secondary_targets.clear()
        self.kalman.reset(320.0, 240.0)
        self.controller.reset()
        self.telemetry.reset()
        self.state = TrackingState.ACQUIRING
        self.state_timer = 0.0
        self.sim_time = 0.0

    def step(self, dt: float) -> DetectionResult:
        """
        Executes one full simulation and tracking cycle at update rate dt:
        1. Update targets kinematics
        2. Apply disturbances (jitter, platform motion)
        3. Render virtual camera viewport (640x480)
        4. Apply atmospheric and image noise
        5. Detect beacon spot via computer vision
        6. Update Kalman Filter state
        7. State machine transitions
        8. Closed-loop gimbal control
        9. Telemetry recording
        """
        start_t = time.perf_counter()
        self.sim_time += dt
        self.state_timer += dt
        
        # 1. Update targets kinematics
        self.primary_target.update(dt, self.env_config.screen_width, self.env_config.screen_height)
        for sec in self.secondary_targets:
            sec.update(dt, self.env_config.screen_width, self.env_config.screen_height)
            
        # 2. Update disturbances (jitter & platform motion)
        (jit_x, jit_y), (plat_x, plat_y) = self.disturbances.update(dt)
        self.camera.jitter_offset_x = jit_x
        self.camera.jitter_offset_y = jit_y
        self.camera.platform_offset_x = plat_x
        self.camera.platform_offset_y = plat_y
        self.camera.update_world_position()
        
        # 3. Render base viewport from virtual environment
        canvas = self.environment.render_viewport_patch(
            self.camera.world_x, self.camera.world_y,
            self.camera.width, self.camera.height
        )
        
        # Render targets
        for sec in self.secondary_targets:
            sec.render_onto_viewport(canvas, self.camera.world_x, self.camera.world_y)
        self.primary_target.render_onto_viewport(canvas, self.camera.world_x, self.camera.world_y)
        
        # 4. Apply atmospheric disturbance and image noise
        self.current_frame = self.disturbances.apply_disturbances_to_frame(canvas)
        
        # 5. Kalman Filter Prediction
        pred_x, pred_y = self.kalman.predict(dt)
        self.latest_pred_x, self.latest_pred_y = pred_x, pred_y
        
        # 6. Computer Vision Detection
        det = self.detector.detect(self.current_frame, predicted_pos=(pred_x, pred_y))
        self.last_detection = det
        
        # 7. State Machine & Kalman Update
        target_in_fov = self.camera.is_point_in_fov(self.primary_target.x, self.primary_target.y)
        
        if det.detected:
            # Measurement update in EKF
            self.kalman.update(det.x, det.y, confidence=det.confidence)
            
            if self.state in [TrackingState.ACQUIRING, TrackingState.SEARCHING, TrackingState.DEAD_RECKONING]:
                self.state = TrackingState.TRACKING
                self.state_timer = 0.0
                
        else:
            # Target not detected in current frame
            if self.state == TrackingState.TRACKING:
                # Transition to Dead Reckoning for short occlusion
                self.state = TrackingState.DEAD_RECKONING
                self.state_timer = 0.0
                
            elif self.state == TrackingState.DEAD_RECKONING:
                # If target missing for > 0.4s, initiate autonomous re-acquisition spiral
                if self.state_timer > 0.4:
                    self.state = TrackingState.SEARCHING
                    self.controller.start_search(self.camera.pan_deg, self.camera.tilt_deg)
                    self.state_timer = 0.0
                    
            elif self.state == TrackingState.SEARCHING:
                # If search times out > 3.5s, mark as lost
                if self.state_timer > self.ctrl_config.search_timeout_s:
                    self.state = TrackingState.LOST

        # 8. Closed-Loop Gimbal Camera Control
        if self.is_autonomous_tracking:
            if self.state in [TrackingState.ACQUIRING, TrackingState.TRACKING]:
                # Track detected position with PID + Kalman feedforward
                tx = det.x if det.detected else pred_x
                ty = det.y if det.detected else pred_y
                vx, vy = self.kalman.velocity
                
                # Reconstruct estimated target world velocity (relative velocity + camera slew velocity)
                v_cam_x = self.camera.pan_velocity_deg_s * self.cam_config.pixels_per_deg_x
                v_cam_y = self.camera.tilt_velocity_deg_s * self.cam_config.pixels_per_deg_y
                ff_world_x = vx + v_cam_x
                ff_world_y = vy + v_cam_y
                
                cmd_pan, cmd_tilt = self.controller.compute_tracking_command(
                    tx, ty, ff_world_x, ff_world_y, dt
                )
                self.camera.apply_pan_tilt_command(cmd_pan, cmd_tilt, dt)
                
            elif self.state == TrackingState.DEAD_RECKONING:
                # Drive camera according to EKF predicted trajectory
                vx, vy = self.kalman.velocity
                cmd_pan, cmd_tilt = self.controller.compute_tracking_command(
                    pred_x, pred_y, vx, vy, dt
                )
                self.camera.apply_pan_tilt_command(cmd_pan, cmd_tilt, dt)
                
            elif self.state == TrackingState.SEARCHING:
                # Execute rapid spiral search pattern
                cmd_pan, cmd_tilt = self.controller.compute_search_command(dt)
                self.camera.apply_pan_tilt_command(cmd_pan, cmd_tilt, dt)

        # 9. Telemetry & Metrics Update
        elapsed = time.perf_counter() - start_t
        fps = 1.0 / max(1e-4, dt)
        latency_ms = elapsed * 1000.0
        
        meas_x = det.x if det.detected else pred_x
        meas_y = det.y if det.detected else pred_y
        
        self.telemetry.record_frame(
            t_sim=self.sim_time,
            state=self.state,
            target_in_fov=target_in_fov,
            detected=det.detected,
            measured_x=meas_x,
            measured_y=meas_y,
            center_x=self.cam_config.center_x,
            center_y=self.cam_config.center_y,
            pan_deg=self.camera.pan_deg,
            tilt_deg=self.camera.tilt_deg,
            target_speed=self.primary_target.speed,
            fps=fps,
            latency_ms=latency_ms,
            snr_db=det.snr_db
        )
        
        return det
