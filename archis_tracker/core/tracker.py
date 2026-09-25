"""Archis production tracking facade backed by the unified deterministic core."""
from __future__ import annotations

import time
from typing import List, Optional

import cv2
import numpy as np

from .camera import VirtualCamera
from .codelock import CodeLock
from .config import (
    AGCMode, CameraConfig, ControllerConfig, DetectorConfig, DisturbanceConfig,
    EnvironmentConfig, TargetConfig, TerminalWorldConfig, TrackingAlgorithm,
    TrackingState,
)
from .contracts import (
    CameraCommand, CanonicalTrackingState, Detection, FramePacket,
    GroundTruthSample, TrackEstimate, TrackingResult,
)
from .controller import GimbalController
from .detector import BeaconDetector, DetectionResult
from .disturbances import DisturbanceEngine
from .environment import VirtualEnvironment
from .kalman_filter import KalmanFilter2D
from .photometry import SpotPhotometry, measurement_sigma_px
from .presets import LoadedPreset, load_and_apply_preset
from .state_machine import StateMachineConfig, TrackingStateMachine
from .target import TargetBeacon, TargetManager
from .telemetry import TelemetryEngine
from .world_model import TwoTerminalWorldModel, WorldGeometrySnapshot


_LEGACY_STATE = {
    CanonicalTrackingState.SEARCH: TrackingState.ACQUIRING,
    CanonicalTrackingState.ACQUIRE: TrackingState.ACQUIRING,
    CanonicalTrackingState.TRACK: TrackingState.TRACKING,
    CanonicalTrackingState.COAST: TrackingState.DEAD_RECKONING,
    CanonicalTrackingState.REACQUIRE: TrackingState.SEARCHING,
}


class TrackingSystem:
    """Compatibility facade used by the existing Archis UI and integrations."""

    def __init__(
        self,
        cam_config: Optional[CameraConfig] = None,
        env_config: Optional[EnvironmentConfig] = None,
        target_config: Optional[TargetConfig] = None,
        disturb_config: Optional[DisturbanceConfig] = None,
        ctrl_config: Optional[ControllerConfig] = None,
        det_config: Optional[DetectorConfig] = None,
        terminal_world_config: Optional[TerminalWorldConfig] = None,
    ) -> None:
        self.cam_config = cam_config or CameraConfig()
        self.env_config = env_config or EnvironmentConfig()
        self.target_config = target_config or TargetConfig()
        self.disturb_config = disturb_config or DisturbanceConfig()
        self.ctrl_config = ctrl_config or ControllerConfig()
        self.det_config = det_config or DetectorConfig()
        self.terminal_world_config = terminal_world_config or TerminalWorldConfig()

        self.environment = VirtualEnvironment(self.env_config)
        self.camera = VirtualCamera(self.cam_config, self.env_config)
        self.disturbances = DisturbanceEngine(self.disturb_config)
        self.detector = BeaconDetector(self.det_config)
        self.kalman = KalmanFilter2D()
        self.controller = GimbalController(self.ctrl_config, self.cam_config)
        self.telemetry = TelemetryEngine()
        self.target_manager = TargetManager(self.target_config)
        self.world_model = TwoTerminalWorldModel(
            self.cam_config, self.env_config, self.terminal_world_config
        )
        self.state_machine = TrackingStateMachine(
            StateMachineConfig(
                confirmation_frames=self.ctrl_config.acquisition_confirmation_frames,
                coast_timeout_s=self.ctrl_config.coast_timeout_s,
                local_reacquire_timeout_s=self.ctrl_config.local_reacquire_timeout_s,
            )
        )
        self.code_lock = self._create_codelock()

        self.state: TrackingState = TrackingState.ACQUIRING
        self.state_timer = 0.0
        self.sim_time = 0.0
        self.frame_index = 0
        self.external_frame_index = 0
        self.current_frame = np.zeros(
            (self.cam_config.viewport_height, self.cam_config.viewport_width), dtype=np.uint8
        )
        self.last_detection = DetectionResult(False)
        self.last_result: TrackingResult | None = None
        self.last_truth: GroundTruthSample | None = None
        self.latest_pred_x = self.cam_config.center_x
        self.latest_pred_y = self.cam_config.center_y
        self.is_autonomous_tracking = True
        self.sensor_obscured = False
        self._ever_acquired = False
        self._base_target_intensity = float(self.target_config.intensity)
        self._external_shape: tuple[int, int] | None = None
        self.world_snapshot: WorldGeometrySnapshot = self.world_model.reset(
            self.camera, self.primary_target, self.secondary_targets
        )

    @property
    def canonical_state(self) -> CanonicalTrackingState:
        return self.state_machine.state

    @property
    def primary_target(self) -> TargetBeacon:
        return self.target_manager.primary_target

    @property
    def secondary_targets(self) -> List[TargetBeacon]:
        return self.target_manager.secondary_targets

    def _create_codelock(self) -> CodeLock | None:
        pattern = self.det_config.code_lock_pattern
        if not pattern:
            return None
        return CodeLock(
            pattern,
            symbol_frames=self.det_config.code_lock_symbol_frames,
            minimum_correlation=self.det_config.code_lock_minimum_correlation,
        )

    def reset(self) -> None:
        self.camera.reset()
        self.target_manager.primary_target.reset_position(
            self.target_config.initial_x if self.target_config.initial_x is not None else self.env_config.screen_width / 2.0,
            self.target_config.initial_y if self.target_config.initial_y is not None else self.env_config.screen_height / 2.0,
        )
        self.target_manager.clear_decoys()
        self.kalman.reset(self.cam_config.center_x, self.cam_config.center_y)
        self.controller.reset()
        self.telemetry.reset()
        self.disturbances.reset()
        self.state_machine.reset()
        if self.code_lock:
            self.code_lock.reset()
        self.detector.target_template = None
        self.detector.last_candidates = []
        self.detector.ai_detector.last_heatmap = None
        self.detector.spot_scale_px = float(self.det_config.fallback_fwhm_px)
        self.last_detection = DetectionResult(False, algorithm_used=self.detector.config.algorithm.value)
        self.current_frame = np.zeros(
            (self.cam_config.viewport_height, self.cam_config.viewport_width), dtype=np.uint8
        )
        self.last_result = None
        self.last_truth = None
        self.state = TrackingState.ACQUIRING
        self.state_timer = self.sim_time = 0.0
        self.frame_index = self.external_frame_index = 0
        self.sensor_obscured = False
        self._ever_acquired = False
        self._external_shape = None
        self.world_snapshot = self.world_model.reset(
            self.camera, self.primary_target, self.secondary_targets
        )

    def spawn_decoy(self, world_x: float, world_y: float, **kwargs) -> TargetBeacon:
        kwargs.setdefault("random_seed", self.target_config.random_seed)
        decoy = self.target_manager.add_decoy(world_x, world_y, **kwargs)
        self._refresh_world_snapshot()
        return decoy

    def clear_decoys(self) -> None:
        self.target_manager.clear_decoys()
        self._refresh_world_snapshot()

    def designate_target_at(self, world_x: float, world_y: float) -> None:
        target = self.target_manager.designate_nearest(world_x, world_y)
        if target:
            vx, vy = self.camera.world_to_viewport(target.x, target.y)
            self.kalman.reset(vx, vy)
            self.detector.target_template = None
            self.state_machine.reset()
            self.state = TrackingState.ACQUIRING
            self._refresh_world_snapshot()

    def move_primary_to(self, world_x: float, world_y: float) -> None:
        self.primary_target.x = self.primary_target.center_x = world_x
        self.primary_target.y = self.primary_target.center_y = world_y
        self._refresh_world_snapshot()

    def set_algorithm(self, algo: TrackingAlgorithm) -> None:
        self.detector.config.algorithm = algo
        self.detector.target_template = None

    def set_agc_mode(self, mode: AGCMode) -> None:
        self.detector.config.agc_mode = mode

    def configure_random_seed(self, seed: int) -> None:
        if seed < 0:
            raise ValueError("random seed cannot be negative")
        self.env_config.random_seed = seed
        self.target_config.random_seed = seed
        self.disturb_config.random_seed = seed
        self.primary_target.config.random_seed = seed
        self.environment = VirtualEnvironment(self.env_config)

    def load_preset(self, path: str) -> LoadedPreset:
        return load_and_apply_preset(self, path)

    def step(self, dt: float) -> DetectionResult:
        if dt <= 0:
            raise ValueError("tracking dt must be positive")
        started = time.perf_counter()
        self.sim_time += dt
        self.frame_index += 1
        self.target_manager.update(dt, self.env_config.screen_width, self.env_config.screen_height)

        (jitter_x, jitter_y), (platform_x, platform_y) = self.disturbances.update(dt)
        self.camera.jitter_offset_x, self.camera.jitter_offset_y = jitter_x, jitter_y
        self.camera.platform_offset_x, self.camera.platform_offset_y = platform_x, platform_y
        if self.cam_config.inertial_stabilization_enabled:
            measured_x, measured_y = self.disturbances.measure_platform_offset(
                jitter_x + platform_x, jitter_y + platform_y,
                self.cam_config.inertial_sensor_noise_px,
            )
            self.camera.apply_inertial_stabilization(measured_x, measured_y)
        else:
            self.camera.update_world_position()
        self.world_snapshot = self.world_model.update(
            dt, self.camera, self.primary_target, self.secondary_targets
        )

        canvas = self.environment.render_viewport_patch(
            self.camera.world_x, self.camera.world_y, self.camera.width, self.camera.height
        )
        self._apply_beacon_code()
        self.target_manager.render_all_onto_viewport(canvas, self.camera.world_x, self.camera.world_y)
        self.current_frame = self.disturbances.apply_disturbances_to_frame(canvas)
        dropout = self.disturbances.is_dropout_active()
        if self.sensor_obscured or dropout:
            self.current_frame.fill(0)

        truth_x, truth_y = self.camera.world_to_viewport(self.primary_target.x, self.primary_target.y)
        self.last_truth = GroundTruthSample(
            truth_x, truth_y,
            bool(self.camera.is_point_in_fov(self.primary_target.x, self.primary_target.y))
            and not (self.sensor_obscured or dropout),
            str(self.primary_target.target_id),
        )
        packet = FramePacket(self.frame_index, self.sim_time, self.current_frame, "simulation")
        detection, result = self._track_packet(packet, dt, apply_camera=True, truth=self.last_truth, started=started)
        self.last_result = result
        return detection

    def _refresh_world_snapshot(self) -> None:
        """Refresh UI geometry after an instantaneous designation/edit."""
        self.world_snapshot = self.world_model.update(
            0.0, self.camera, self.primary_target, self.secondary_targets
        )

    def step_external_frame(
        self, frame: np.ndarray, dt: float, truth: GroundTruthSample | None = None
    ) -> DetectionResult:
        if dt <= 0:
            raise ValueError("tracking dt must be positive")
        started = time.perf_counter()
        if frame.ndim == 3 and frame.shape[2] == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        elif frame.ndim == 3 and frame.shape[2] == 4:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
        elif frame.ndim == 3 and frame.shape[2] == 1:
            gray = frame[:, :, 0]
        else:
            gray = frame
        if gray.ndim != 2:
            raise ValueError("external frame must be grayscale or BGR")
        self.current_frame = np.clip(gray, 0, 255).astype(np.uint8)
        height, width = self.current_frame.shape
        if self._external_shape != (height, width):
            self._external_shape = (height, width)
            self.kalman.reset(width / 2.0, height / 2.0)
            self.state_machine.reset()
        self.sim_time += dt
        packet = FramePacket(self.external_frame_index, self.sim_time, self.current_frame, "external")
        self.external_frame_index += 1
        self.last_truth = truth
        detection, result = self._track_packet(packet, dt, apply_camera=False, truth=truth, started=started)
        self.last_result = result
        return detection

    def process_packet(
        self, packet: FramePacket, truth: GroundTruthSample | None = None
    ) -> TrackingResult:
        """Process a contract frame while preserving its source metadata."""
        dt = packet.timestamp_s - self.sim_time if packet.timestamp_s > self.sim_time else 1.0 / 30.0
        self.external_frame_index = packet.index
        self.sim_time = max(0.0, packet.timestamp_s - dt)
        self.step_external_frame(packet.image, dt, truth)
        assert self.last_result is not None
        self.last_result = TrackingResult(
            packet, self.last_result.state, self.last_result.detections,
            self.last_result.selected, self.last_result.estimate, self.last_result.command,
            self.last_result.processing_time_ms, self.last_result.diagnostics,
        )
        return self.last_result

    def _track_packet(
        self, packet: FramePacket, dt: float, *, apply_camera: bool,
        truth: GroundTruthSample | None, started: float,
    ) -> tuple[DetectionResult, TrackingResult]:
        pred_x, pred_y = self.kalman.predict(dt)
        self.latest_pred_x, self.latest_pred_y = pred_x, pred_y
        periodic_scan = packet.index % max(1, self.ctrl_config.periodic_full_scan_frames) == 0
        use_gate = self.state_machine.use_prediction_gate and not periodic_scan
        # A periodic safety scan may search the whole image, but an unrelated
        # bright candidate must still not be allowed to jump a confirmed
        # estimate.  Disable this defensive filter gate only while acquiring
        # or globally reacquiring a target.
        filter_gate = self.state_machine.state in {
            CanonicalTrackingState.TRACK, CanonicalTrackingState.COAST,
        }
        detection = self.detector.detect(
            packet.image,
            predicted_pos=(pred_x, pred_y) if use_gate else None,
            cov_matrix=self.kalman.innovation_covariance if use_gate else None,
        )
        candidates = tuple(self._contract_detection(item) for item in self.detector.last_candidates)
        if detection.detected and not candidates:
            candidates = (self._contract_detection(detection),)

        if self.code_lock is not None:
            verified = self.code_lock.filter(packet.image, candidates, packet.index)
            candidates = verified
            if verified:
                detection = self._legacy_detection(verified[0], detection)
            else:
                detection = DetectionResult(
                    False, gate_bbox=detection.gate_bbox,
                    algorithm_used=detection.algorithm_used,
                    heatmap=detection.heatmap, heatmap_bbox=detection.heatmap_bbox,
                )

        measurement_accepted: bool | None = None
        optical_sigma_px: float | None = None
        if detection.detected:
            if detection.fwhm_px is not None and detection.snr_aperture is not None:
                optical_sigma_px = measurement_sigma_px(
                    SpotPhotometry(
                        detection.fwhm_px, detection.snr_aperture,
                        detection.snr_peak, 0.0, 0.0,
                        detection.clipped, detection.saturated_fraction,
                    ),
                    calibration=self.det_config.measurement_noise_calibration,
                    floor_px=self.det_config.measurement_noise_floor_px,
                    ceiling_px=self.det_config.measurement_noise_ceiling_px,
                )
            measurement_accepted = self.kalman.update(
                detection.x,
                detection.y,
                detection.confidence,
                gate_threshold_chi2=(
                    self.det_config.kalman_gate_threshold_chi2 if filter_gate else None
                ),
                measurement_sigma_px=optical_sigma_px,
            )
            if not measurement_accepted:
                detection = DetectionResult(
                    False, gate_bbox=detection.gate_bbox,
                    confidence=detection.confidence,
                    peak_intensity=detection.peak_intensity,
                    snr_db=detection.snr_db,
                    algorithm_used=detection.algorithm_used,
                    heatmap=detection.heatmap,
                    heatmap_bbox=detection.heatmap_bbox,
                    fwhm_px=detection.fwhm_px,
                    snr_aperture=detection.snr_aperture,
                    snr_peak=detection.snr_peak,
                    clipped=detection.clipped,
                    saturated_fraction=detection.saturated_fraction,
                )

        previous_state = self.state_machine.state
        canonical = self.state_machine.update(detection.detected, dt)
        self.state_timer = self.state_machine.state_elapsed_s
        self.state = _LEGACY_STATE[canonical]
        if canonical == CanonicalTrackingState.TRACK:
            self._ever_acquired = True
        if canonical == CanonicalTrackingState.REACQUIRE and previous_state != canonical:
            self.controller.start_search(self.camera.pan_deg, self.camera.tilt_deg)

        command = self._command_for_state(
            canonical, detection, pred_x, pred_y, dt,
            frame_width=packet.image.shape[1], frame_height=packet.image.shape[0],
            apply_camera=apply_camera,
        )
        if apply_camera and self.is_autonomous_tracking and command is not None:
            self.camera.apply_pan_tilt_command(command.pan_rate_deg_s, command.tilt_rate_deg_s, dt)
            # The rendered frame used the pre-command pose; the UI snapshot
            # represents the newly commanded gimbal pose for the next frame.
            self._refresh_world_snapshot()

        selected = self._contract_detection(detection) if detection.detected else None
        estimate = self._estimate(canonical, detection, pred_x, pred_y)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        center_x, center_y = packet.image.shape[1] / 2.0, packet.image.shape[0] / 2.0
        measured_x = detection.x if detection.detected else pred_x
        measured_y = detection.y if detection.detected else pred_y
        self.telemetry.record_frame(
            t_sim=packet.timestamp_s, state=self.state,
            target_in_fov=truth.visible if truth is not None else detection.detected,
            detected=detection.detected and canonical == CanonicalTrackingState.TRACK,
            measured_x=measured_x, measured_y=measured_y,
            center_x=center_x, center_y=center_y,
            pan_deg=self.camera.pan_deg if apply_camera else 0.0,
            tilt_deg=self.camera.tilt_deg if apply_camera else 0.0,
            target_speed=self.primary_target.speed if apply_camera else 0.0,
            fps=1.0 / dt, latency_ms=elapsed_ms, snr_db=detection.snr_db,
            truth_x=None if truth is None else truth.x_px,
            truth_y=None if truth is None else truth.y_px,
            truth_visible=None if truth is None else truth.visible,
        )
        diagnostics = {
            "search_scope": "full" if periodic_scan else self.state_machine.search_scope,
            "identity_status": None if self.code_lock is None else self.code_lock.status,
            "identity_correlation": None if self.code_lock is None else self.code_lock.best_correlation,
            "truth_available": truth is not None,
            "innovation_distance_sq": (
                self.kalman.last_innovation_distance_sq
                if measurement_accepted is not None else None
            ),
            "measurement_accepted": measurement_accepted,
            "measurement_sigma_px": optical_sigma_px,
            "fwhm_px": detection.fwhm_px,
            "snr_aperture": detection.snr_aperture,
            "snr_peak": detection.snr_peak,
            "clipped": detection.clipped,
            "saturated_fraction": detection.saturated_fraction,
            "innovation_gate_enabled": filter_gate,
            "latency_compensation_s": self.ctrl_config.latency_compensation_s,
        }
        if apply_camera:
            diagnostics.update({
                "terminal_range_m": self.world_snapshot.separation_m,
                "los_azimuth_deg": self.world_snapshot.line_of_sight_azimuth_deg,
                "los_elevation_deg": self.world_snapshot.line_of_sight_elevation_deg,
                "relative_azimuth_deg": self.world_snapshot.relative_azimuth_deg,
                "relative_elevation_deg": self.world_snapshot.relative_elevation_deg,
                "terminal_in_fov": self.world_snapshot.transmitter_in_fov,
                "decoy_terminal_count": len(self.world_snapshot.decoys),
            })
        result = TrackingResult(packet, canonical, candidates, selected, estimate, command, elapsed_ms, diagnostics)
        self.last_detection = detection
        return detection, result

    def _command_for_state(
        self, state: CanonicalTrackingState, detection: DetectionResult,
        pred_x: float, pred_y: float, dt: float, *,
        frame_width: int, frame_height: int, apply_camera: bool,
    ) -> CameraCommand | None:
        if not self.is_autonomous_tracking:
            return None
        if state in {CanonicalTrackingState.ACQUIRE, CanonicalTrackingState.TRACK, CanonicalTrackingState.COAST}:
            target_x = detection.x if detection.detected else pred_x
            target_y = detection.y if detection.detected else pred_y
            velocity_x, velocity_y = self.kalman.velocity
            acceleration_x, acceleration_y = self.kalman.acceleration
            lead_s = float(np.clip(self.ctrl_config.latency_compensation_s, 0.0, 2.0))
            if lead_s > 0.0 and self.kalman.is_initialized:
                target_x += velocity_x * lead_s + 0.5 * acceleration_x * lead_s * lead_s
                target_y += velocity_y * lead_s + 0.5 * acceleration_y * lead_s * lead_s
            px_per_deg_x = frame_width / self.cam_config.fov_x_deg
            px_per_deg_y = frame_height / self.cam_config.fov_y_deg
            camera_vx = self.camera.pan_velocity_deg_s * px_per_deg_x if apply_camera else 0.0
            camera_vy = self.camera.tilt_velocity_deg_s * px_per_deg_y if apply_camera else 0.0
            pan, tilt = self.controller.compute_tracking_command(
                target_x, target_y, velocity_x + camera_vx, velocity_y + camera_vy, dt,
                sensor_width_px=frame_width, sensor_height_px=frame_height,
            )
            return CameraCommand(pan, tilt)
        if state == CanonicalTrackingState.REACQUIRE:
            pan, tilt = self.controller.compute_search_command(dt)
            return CameraCommand(pan, tilt)
        return None

    def _estimate(
        self, state: CanonicalTrackingState, detection: DetectionResult,
        pred_x: float, pred_y: float,
    ) -> TrackEstimate:
        x, y = self.kalman.position if self.kalman.is_initialized else (pred_x, pred_y)
        vx, vy = self.kalman.velocity
        covariance = tuple(tuple(float(value) for value in row) for row in self.kalman.cov)
        return TrackEstimate(
            x, y, vx, vy, covariance,
            detection.confidence if detection.detected else 0.0, state,
        )

    @staticmethod
    def _contract_detection(item: DetectionResult) -> Detection:
        return Detection(
            item.x, item.y, item.confidence, float(item.bbox[2]), float(item.bbox[3]),
            item.algorithm_used,
            item.confidence if "AI" in item.algorithm_used or "Hybrid" in item.algorithm_used else None,
            None,
            item.fwhm_px, item.snr_aperture, item.snr_peak,
            item.clipped, item.saturated_fraction,
        )

    @staticmethod
    def _legacy_detection(item: Detection, template: DetectionResult) -> DetectionResult:
        width, height = max(1, round(item.width_px)), max(1, round(item.height_px))
        return DetectionResult(
            True, item.x_px, item.y_px,
            (round(item.x_px - width / 2), round(item.y_px - height / 2), width, height),
            template.gate_bbox, item.confidence, template.peak_intensity, template.snr_db,
            template.algorithm_used, template.heatmap, False, template.heatmap_bbox,
            item.fwhm_px if item.fwhm_px is not None else template.fwhm_px,
            item.snr_aperture if item.snr_aperture is not None else template.snr_aperture,
            item.snr_peak if item.snr_peak is not None else template.snr_peak,
            item.clipped or template.clipped,
            max(item.saturated_fraction, template.saturated_fraction),
        )

    def _apply_beacon_code(self) -> None:
        if not self.det_config.code_lock_pattern:
            self.primary_target.intensity = self._base_target_intensity
            return
        period = self.det_config.code_lock_pattern
        symbol_frames = max(1, self.det_config.code_lock_symbol_frames)
        bit = period[(self.frame_index // symbol_frames) % len(period)]
        self.primary_target.intensity = (
            self._base_target_intensity if bit == "1" else max(32.0, self._base_target_intensity * 0.35)
        )
