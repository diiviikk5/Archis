"""
Archis Optical Tracker - Integrated Production Tracking System Engine
Coordinates Environment, Multi-Target Manager, Gimbal-Camera, Disturbances,
Multi-Algorithm Detector, 6-State EKF, Dual-Loop Controller, and Telemetry.
"""
import numpy as np
import cv2
import time
from typing import Tuple, List, Optional
from .config import (CameraConfig, EnvironmentConfig, TargetConfig, 
                     DisturbanceConfig, ControllerConfig, DetectorConfig,
                     TrackingState, TrackingAlgorithm, AGCMode)
from .environment import VirtualEnvironment
from .target import TargetBeacon, TargetManager
from .camera import VirtualCamera
from .disturbances import DisturbanceEngine
from .detector import BeaconDetector, DetectionResult
from .kalman_filter import KalmanFilter2D
from .controller import GimbalController
from .telemetry import TelemetryEngine
from .presets import load_and_apply_preset, LoadedPreset


class TrackingSystem:
    def __init__(self, cam_config: Optional[CameraConfig] = None,
                 env_config: Optional[EnvironmentConfig] = None,
                 target_config: Optional[TargetConfig] = None,
                 disturb_config: Optional[DisturbanceConfig] = None,
                 ctrl_config: Optional[ControllerConfig] = None,
                 det_config: Optional[DetectorConfig] = None):
                 
        self.cam_config = cam_config or CameraConfig()
        self.env_config = env_config or EnvironmentConfig()
        self.target_config = target_config or TargetConfig()
        self.disturb_config = disturb_config or DisturbanceConfig()
        self.ctrl_config = ctrl_config or ControllerConfig()
        self.det_config = det_config or DetectorConfig()
        
        # Sub-systems
        self.environment = VirtualEnvironment(self.env_config)
        self.camera = VirtualCamera(self.cam_config, self.env_config)
        self.disturbances = DisturbanceEngine(self.disturb_config)
        self.detector = BeaconDetector(self.det_config)
        self.kalman = KalmanFilter2D()
        self.controller = GimbalController(self.ctrl_config, self.cam_config)
        self.telemetry = TelemetryEngine()
        
        # Multi-Target Coordinator
        self.target_manager = TargetManager(self.target_config)
        
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
        self.sensor_obscured: bool = False

    @property
    def primary_target(self) -> TargetBeacon:
        return self.target_manager.primary_target

    @property
    def secondary_targets(self) -> List[TargetBeacon]:
        return self.target_manager.secondary_targets

    def reset(self):
        """Resets the entire system to initial baseline parameters."""
        self.camera.reset()
        self.target_manager.primary_target.reset_position(1000.0, 1000.0)
        self.target_manager.clear_decoys()
        self.kalman.reset(320.0, 240.0)
        self.controller.reset()
        self.telemetry.reset()
        self.detector.target_template = None
        self.state = TrackingState.ACQUIRING
        self.state_timer = 0.0
        self.sim_time = 0.0
        self.sensor_obscured = False

    def spawn_decoy(self, world_x: float, world_y: float, **kwargs) -> TargetBeacon:
        """Injects a secondary optical decoy into the virtual scene."""
        return self.target_manager.add_decoy(world_x, world_y, **kwargs)

    def clear_decoys(self):
        self.target_manager.clear_decoys()

    def designate_target_at(self, world_x: float, world_y: float):
        """Promotes the target closest to (world_x, world_y) to primary lock."""
        new_pri = self.target_manager.designate_nearest(world_x, world_y)
        if new_pri:
            # Re-init Kalman filter on new target viewport projection
            vx, vy = self.camera.world_to_viewport(new_pri.x, new_pri.y)
            self.kalman.reset(vx, vy)
            self.detector.target_template = None
            self.state = TrackingState.ACQUIRING
            self.state_timer = 0.0

    def move_primary_to(self, world_x: float, world_y: float):
        """Manually moves/drags the primary target to test sudden re-acquisition."""
        self.primary_target.x = world_x
        self.primary_target.y = world_y
        self.primary_target.center_x = world_x
        self.primary_target.center_y = world_y

    def set_algorithm(self, algo: TrackingAlgorithm):
        self.detector.config.algorithm = algo
        self.detector.target_template = None

    def set_agc_mode(self, mode: AGCMode):
        self.detector.config.agc_mode = mode

    def load_preset(self, path: str) -> LoadedPreset:
        return load_and_apply_preset(self, path)

    def step(self, dt: float) -> DetectionResult:
        start_t = time.perf_counter()
        self.sim_time += dt
        self.state_timer += dt
        
        # 1. Update targets kinematics
        self.target_manager.update(dt, self.env_config.screen_width, self.env_config.screen_height)
            
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
        
        # Render primary target and all secondary decoys
        self.target_manager.render_all_onto_viewport(canvas, self.camera.world_x, self.camera.world_y)
        
        # 4. Apply atmospheric disturbance and image noise
        self.current_frame = self.disturbances.apply_disturbances_to_frame(canvas)
        if self.sensor_obscured:
            self.current_frame.fill(0)
        
        # 5. Kalman Filter Prediction
        pred_x, pred_y = self.kalman.predict(dt)
        self.latest_pred_x, self.latest_pred_y = pred_x, pred_y
        
        # 6. Computer Vision Detection with Innovation Gating
        cov_s = self.kalman.innovation_covariance
        det = self.detector.detect(self.current_frame, predicted_pos=(pred_x, pred_y), cov_matrix=cov_s)
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
                self.state = TrackingState.DEAD_RECKONING
                self.state_timer = 0.0
                
            elif self.state == TrackingState.DEAD_RECKONING:
                # If target missing for > 0.4s, initiate autonomous re-acquisition spiral
                if self.state_timer > 0.4:
                    self.state = TrackingState.SEARCHING
                    self.controller.start_search(self.camera.pan_deg, self.camera.tilt_deg)
                    self.state_timer = 0.0
                    
            elif self.state == TrackingState.SEARCHING:
                if self.state_timer > self.ctrl_config.search_timeout_s:
                    self.state = TrackingState.LOST

        # 8. Closed-Loop Gimbal Camera Control
        if self.is_autonomous_tracking:
            if self.state in [TrackingState.ACQUIRING, TrackingState.TRACKING]:
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
                vx, vy = self.kalman.velocity
                cmd_pan, cmd_tilt = self.controller.compute_tracking_command(
                    pred_x, pred_y, vx, vy, dt
                )
                self.camera.apply_pan_tilt_command(cmd_pan, cmd_tilt, dt)
                
            elif self.state == TrackingState.SEARCHING:
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

    def step_external_frame(self, frame: np.ndarray, dt: float) -> DetectionResult:
        """Track a video frame while bypassing virtual target and PTZ generation."""
        start_t = time.perf_counter()
        self.sim_time += dt
        self.state_timer += dt
        if frame.ndim == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if frame.shape != (self.cam_config.viewport_height, self.cam_config.viewport_width):
            frame = cv2.resize(
                frame,
                (self.cam_config.viewport_width, self.cam_config.viewport_height),
                interpolation=cv2.INTER_AREA,
            )
        self.current_frame = np.clip(frame, 0, 255).astype(np.uint8)

        pred_x, pred_y = self.kalman.predict(dt)
        self.latest_pred_x, self.latest_pred_y = pred_x, pred_y
        detection = self.detector.detect(
            self.current_frame,
            predicted_pos=(pred_x, pred_y),
            cov_matrix=self.kalman.innovation_covariance,
        )
        self.last_detection = detection
        if detection.detected:
            self.kalman.update(detection.x, detection.y, confidence=detection.confidence)
            if self.state != TrackingState.TRACKING:
                self.state = TrackingState.TRACKING
                self.state_timer = 0.0
        elif self.state == TrackingState.TRACKING:
            self.state = TrackingState.DEAD_RECKONING
            self.state_timer = 0.0
        elif self.state == TrackingState.DEAD_RECKONING and self.state_timer > 0.4:
            self.state = TrackingState.SEARCHING
            self.state_timer = 0.0
        elif self.state == TrackingState.SEARCHING and self.state_timer > self.ctrl_config.search_timeout_s:
            self.state = TrackingState.LOST

        latency_ms = (time.perf_counter() - start_t) * 1000.0
        measured_x = detection.x if detection.detected else pred_x
        measured_y = detection.y if detection.detected else pred_y
        self.telemetry.record_frame(
            t_sim=self.sim_time,
            state=self.state,
            target_in_fov=detection.detected,
            detected=detection.detected,
            measured_x=measured_x,
            measured_y=measured_y,
            center_x=self.cam_config.center_x,
            center_y=self.cam_config.center_y,
            pan_deg=0.0,
            tilt_deg=0.0,
            target_speed=0.0,
            fps=1.0 / max(1e-4, dt),
            latency_ms=latency_ms,
            snr_db=detection.snr_db,
        )
        return detection
