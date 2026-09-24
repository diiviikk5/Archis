"""Versioned scenario loading with in-memory migration of Archis v1 presets."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from .config import (
    AtmosphericCondition, CameraConfig, ControllerConfig, DetectorConfig,
    DisturbanceConfig, EnvironmentConfig, MotionTrajectory, PlatformMotionType,
    TargetConfig, TargetShape, TerminalWorldConfig, TrackingAlgorithm,
)


class ScenarioError(ValueError):
    pass


DEFAULT_SCENARIO: dict[str, Any] = {
    "schema_version": 2,
    "name": "Archis nominal tracking",
    "description": "Deterministic FSOC coarse-alignment scenario",
    "camera": {
        "viewport_px": [640, 480], "fov_deg": [4.0, 3.0], "update_hz": 30.0,
        "max_rate_deg_s": [5.0, 5.0], "max_acceleration_deg_s2": 25.0,
    },
    "world": {
        "size_px": [2000, 2000], "star_count": 250,
        "nominal_range_m": 1000.0,
        "receiver_position_m": [0.0, 0.0, 0.0],
        "receiver_velocity_m_s": [0.0, 0.0, 0.0],
        "receiver_orientation_deg": [0.0, 0.0, 0.0],
    },
    "target": {
        "shape": "Square", "size_px": [10, 10], "trajectory": "Figure of 8",
        "speed_px_s": 45.0, "intensity": 255.0, "initial_location": "center",
    },
    "disturbances": {
        "atmosphere": "Clear", "atmosphere_strength": 0.0,
        "turbulence_warp_px": 0.0, "turbulence_blur_sigma_px": 0.0,
        "scintillation_log_std": 0.0,
        "illumination_flicker_fraction": 0.0, "illumination_flicker_hz": 3.0,
        "gaussian_noise_std": 0.0, "salt_pepper_fraction": 0.0,
        "camera_jitter_max_px": 0.0, "platform_motion": "None",
        "platform_motion_max_px": 0.0,
        "dropout": {
            "enabled": False, "start_s": 0.0, "duration_s": 0.0,
            "burst_enabled": False, "mean_clear_s": 8.0, "mean_loss_s": 0.25,
        },
    },
    "detector": {
        "algorithm": "HYBRID", "code_lock": None,
        "innovation_gate_chi2": 10000.0,
    },
    "controller": {
        "coast_timeout_s": 0.4, "local_reacquire_timeout_s": 0.6,
        "latency_compensation_s": 0.0,
    },
    "evaluation": {"duration_s": 60.0, "random_seed": 26169},
}


@dataclass(frozen=True, slots=True)
class Scenario:
    data: Mapping[str, Any]
    path: Path | None = None

    @property
    def name(self) -> str:
        return str(self.data["name"])

    @property
    def seed(self) -> int:
        return int(self.data["evaluation"]["random_seed"])

    @property
    def duration_s(self) -> float:
        return float(self.data["evaluation"]["duration_s"])


def load_scenario(path: str | Path) -> Scenario:
    source = Path(path)
    if not source.exists():
        from archis_tracker.resources import resource_path
        packaged = resource_path(source)
        if packaged.exists():
            source = packaged
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ScenarioError(f"could not read scenario: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ScenarioError(f"invalid JSON at line {exc.lineno}: {exc.msg}") from exc
    return Scenario(validate_scenario(raw), source)


def validate_scenario(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ScenarioError("scenario root must be an object")
    data = _migrate_legacy(raw) if raw.get("schema_version") is None else deepcopy(raw)
    if data.get("schema_version") != 2:
        raise ScenarioError("only scenario schema_version 2 is supported")
    required = {"name", "camera", "world", "target", "disturbances", "detector", "controller", "evaluation"}
    missing = sorted(required - data.keys())
    if missing:
        raise ScenarioError(f"scenario is missing: {', '.join(missing)}")
    camera = _mapping(data["camera"], "camera")
    world = _mapping(data["world"], "world")
    target = _mapping(data["target"], "target")
    disturbance = _mapping(data["disturbances"], "disturbances")
    detector = _mapping(data["detector"], "detector")
    controller = _mapping(data["controller"], "controller")
    evaluation = _mapping(data["evaluation"], "evaluation")
    _pair(camera.get("viewport_px"), "camera.viewport_px", 1, 16384)
    _pair(camera.get("fov_deg"), "camera.fov_deg", 0.01, 180)
    _pair(camera.get("max_rate_deg_s"), "camera.max_rate_deg_s", 0.1, 20)
    _number(camera.get("max_acceleration_deg_s2", 25), "camera.max_acceleration_deg_s2", 0.1, 1000)
    _number(camera.get("update_hz"), "camera.update_hz", 1, 240)
    world_size = _pair(world.get("size_px"), "world.size_px", 640, 100000)
    _integer(world.get("star_count", 250), "world.star_count", 0, 1_000_000)
    _number(world.get("nominal_range_m", 1000.0), "world.nominal_range_m", 1, 100_000_000)
    _triple(world.get("receiver_position_m", [0, 0, 0]), "world.receiver_position_m", -100_000_000, 100_000_000)
    _triple(world.get("receiver_velocity_m_s", [0, 0, 0]), "world.receiver_velocity_m_s", -100_000, 100_000)
    _triple(world.get("receiver_orientation_deg", [0, 0, 0]), "world.receiver_orientation_deg", -360, 360)
    _validate_target(target, "target")
    _validate_target_position(target, "target", world_size)
    extra_targets = data.get("targets", [])
    if not isinstance(extra_targets, list):
        raise ScenarioError("targets must be an array")
    for index, item in enumerate(extra_targets):
        _validate_target(_mapping(item, f"targets[{index}]"), f"targets[{index}]")
        _validate_target_position(item, f"targets[{index}]", world_size)
    _enum_value(disturbance.get("atmosphere", "Clear"), AtmosphericCondition, "disturbances.atmosphere")
    _enum_value(disturbance.get("platform_motion", "None"), PlatformMotionType, "disturbances.platform_motion")
    _number(disturbance.get("atmosphere_strength", 0), "disturbances.atmosphere_strength", 0, 1)
    _number(disturbance.get("turbulence_warp_px", 0), "disturbances.turbulence_warp_px", 0, 50)
    _number(disturbance.get("turbulence_blur_sigma_px", 0), "disturbances.turbulence_blur_sigma_px", 0, 20)
    _number(disturbance.get("scintillation_log_std", 0), "disturbances.scintillation_log_std", 0, 1.5)
    _number(disturbance.get("illumination_flicker_fraction", 0), "disturbances.illumination_flicker_fraction", 0, .95)
    _number(disturbance.get("illumination_flicker_hz", 3), "disturbances.illumination_flicker_hz", 0, 100)
    _number(disturbance.get("gaussian_noise_std", 0), "disturbances.gaussian_noise_std", 0, 100)
    _number(disturbance.get("salt_pepper_fraction", 0), "disturbances.salt_pepper_fraction", 0, 0.25)
    _number(disturbance.get("camera_jitter_max_px", 0), "disturbances.camera_jitter_max_px", 0, 100)
    _number(disturbance.get("platform_motion_max_px", 0), "disturbances.platform_motion_max_px", 0, 100)
    _enum_value(str(detector.get("algorithm", "HYBRID")).upper(), TrackingAlgorithm, "detector.algorithm", by_name=True)
    _number(detector.get("innovation_gate_chi2", 10000), "detector.innovation_gate_chi2", 1, 1000000)
    code_lock = detector.get("code_lock")
    if code_lock is not None:
        code_lock = _mapping(code_lock, "detector.code_lock")
        pattern = code_lock.get("pattern")
        if not isinstance(pattern, str) or len(pattern) < 7 or set(pattern) != {"0", "1"}:
            raise ScenarioError("detector.code_lock.pattern must contain 0 and 1 and be at least seven bits")
        _integer(code_lock.get("symbol_frames", 1), "detector.code_lock.symbol_frames", 1, 1000)
        _number(code_lock.get("minimum_correlation", .7), "detector.code_lock.minimum_correlation", 0, 1)
    _number(controller.get("coast_timeout_s", .4), "controller.coast_timeout_s", 0, 60)
    _number(controller.get("local_reacquire_timeout_s", .6), "controller.local_reacquire_timeout_s", 0, 60)
    _number(controller.get("latency_compensation_s", 0), "controller.latency_compensation_s", 0, 2)
    _number(evaluation.get("duration_s"), "evaluation.duration_s", 0.01, 86400)
    if isinstance(evaluation.get("random_seed"), bool) or not isinstance(evaluation.get("random_seed"), int):
        raise ScenarioError("evaluation.random_seed must be an integer")
    dropout = disturbance.get("dropout", {})
    if not isinstance(dropout, dict):
        raise ScenarioError("disturbances.dropout must be an object")
    _boolean_value(dropout.get("enabled", False), "disturbances.dropout.enabled")
    _boolean_value(dropout.get("burst_enabled", False), "disturbances.dropout.burst_enabled")
    _number(dropout.get("start_s", 0), "disturbances.dropout.start_s", 0, 86400)
    _number(dropout.get("duration_s", 0), "disturbances.dropout.duration_s", 0, 86400)
    _number(dropout.get("mean_clear_s", 8), "disturbances.dropout.mean_clear_s", 0.001, 86400)
    _number(dropout.get("mean_loss_s", .25), "disturbances.dropout.mean_loss_s", 0.001, 86400)
    return data


def _migrate_legacy(raw: Mapping[str, Any]) -> dict[str, Any]:
    data = deepcopy(DEFAULT_SCENARIO)
    data["name"] = str(raw.get("name") or data["name"])
    data["description"] = str(raw.get("description") or data["description"])
    target = raw.get("target", {})
    camera = raw.get("camera", {})
    disturbances = raw.get("disturbances", {})
    if not all(isinstance(item, dict) for item in (target, camera, disturbances)):
        raise ScenarioError("legacy target, camera and disturbances must be objects")
    if "shape" in target: data["target"]["shape"] = target["shape"]
    if "size" in target: data["target"]["size_px"] = [target["size"], target["size"]]
    if "trajectory" in target: data["target"]["trajectory"] = target["trajectory"]
    if "speed" in target: data["target"]["speed_px_s"] = target["speed"]
    if "intensity" in target: data["target"]["intensity"] = target["intensity"]
    if "fov_x_deg" in camera or "fov_y_deg" in camera:
        data["camera"]["fov_deg"] = [camera.get("fov_x_deg", 4.0), camera.get("fov_y_deg", 3.0)]
    if "max_pan_speed_deg_s" in camera or "max_tilt_speed_deg_s" in camera:
        data["camera"]["max_rate_deg_s"] = [camera.get("max_pan_speed_deg_s", 5.0), camera.get("max_tilt_speed_deg_s", 5.0)]
    data["disturbances"].update({
        "atmosphere": disturbances.get("atmospheric_condition", "Clear"),
        "atmosphere_strength": disturbances.get("atmospheric_severity", 0.0),
        "turbulence_warp_px": disturbances.get("turbulence_warp_px", 0.0),
        "turbulence_blur_sigma_px": disturbances.get("turbulence_blur_sigma_px", 0.0),
        "scintillation_log_std": disturbances.get("scintillation_log_std", 0.0),
        "illumination_flicker_fraction": disturbances.get("illumination_flicker_fraction", 0.0),
        "illumination_flicker_hz": disturbances.get("illumination_flicker_hz", 3.0),
        "gaussian_noise_std": disturbances.get("gaussian_noise_std", 0.0) if disturbances.get("enable_gaussian_noise") else 0.0,
        "salt_pepper_fraction": disturbances.get("salt_pepper_ratio", 0.0) if disturbances.get("enable_salt_pepper") else 0.0,
        "camera_jitter_max_px": disturbances.get("max_camera_jitter_px", 0.0) if disturbances.get("enable_camera_jitter") else 0.0,
        "platform_motion": disturbances.get("platform_motion_type", "None") if disturbances.get("enable_platform_motion") else "None",
        "platform_motion_max_px": disturbances.get("platform_motion_amplitude_px", 0.0) if disturbances.get("enable_platform_motion") else 0.0,
    })
    if isinstance(disturbances.get("dropout"), dict):
        data["disturbances"]["dropout"].update(disturbances["dropout"])
    return data


def _number(value: Any, name: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= float(value) <= high:
        raise ScenarioError(f"{name} must be a number between {low:g} and {high:g}")
    return float(value)


def _integer(value: Any, name: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ScenarioError(f"{name} must be an integer between {low} and {high}")
    return value


def _boolean_value(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ScenarioError(f"{name} must be true or false")
    return value


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ScenarioError(f"{name} must be an object")
    return value


def _enum_value(value: Any, enum_type, name: str, *, by_name: bool = False) -> None:
    try:
        enum_type[str(value)] if by_name else enum_type(value)
    except (KeyError, TypeError, ValueError) as exc:
        choices = ", ".join(item.name if by_name else str(item.value) for item in enum_type)
        raise ScenarioError(f"{name} must be one of: {choices}") from exc


def _validate_target(target: Mapping[str, Any], name: str) -> None:
    _enum_value(target.get("shape"), TargetShape, f"{name}.shape")
    _enum_value(target.get("trajectory"), MotionTrajectory, f"{name}.trajectory")
    _pair(target.get("size_px"), f"{name}.size_px", 1, 100)
    _number(target.get("speed_px_s"), f"{name}.speed_px_s", 0, 5000)
    _number(target.get("intensity", 255), f"{name}.intensity", 1, 255)
    if target.get("range_m") is not None:
        _number(target["range_m"], f"{name}.range_m", 1, 100_000_000)
    if target.get("orientation_deg") is not None:
        _triple(target["orientation_deg"], f"{name}.orientation_deg", -360, 360)
    if "initial_position_px" in target:
        _pair(target["initial_position_px"], f"{name}.initial_position_px", 0, 100000)
    location = str(target.get("initial_location", "center")).lower()
    allowed = {
        "center", "left", "right", "top", "bottom", "top_left", "top_right",
        "bottom_left", "bottom_right",
    }
    if location not in allowed:
        raise ScenarioError(f"{name}.initial_location must be one of: {', '.join(sorted(allowed))}")


def _validate_target_position(target: Mapping[str, Any], name: str, world_size: tuple[float, float]) -> None:
    if "initial_position_px" not in target:
        return
    x_px, y_px = (float(value) for value in target["initial_position_px"])
    if x_px > world_size[0] or y_px > world_size[1]:
        raise ScenarioError(f"{name}.initial_position_px must be inside world.size_px")


def _pair(value: Any, name: str, low: float, high: float) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ScenarioError(f"{name} must contain two numbers")
    return _number(value[0], f"{name}[0]", low, high), _number(value[1], f"{name}[1]", low, high)


def _triple(value: Any, name: str, low: float, high: float) -> tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ScenarioError(f"{name} must contain three numbers")
    return (
        _number(value[0], f"{name}[0]", low, high),
        _number(value[1], f"{name}[1]", low, high),
        _number(value[2], f"{name}[2]", low, high),
    )


def tracker_from_scenario(scenario: Scenario):
    """Build a TrackingSystem from validated schema-v2 data."""
    from .tracker import TrackingSystem

    data = scenario.data
    camera, world = data["camera"], data["world"]
    configured_targets = list(data.get("targets", []))
    target = configured_targets[0] if configured_targets else data["target"]
    disturbance, detector, controller = data["disturbances"], data["detector"], data["controller"]
    width, height = (int(value) for value in camera["viewport_px"])
    fov_x, fov_y = (float(value) for value in camera["fov_deg"])
    pan_rate, tilt_rate = (float(value) for value in camera["max_rate_deg_s"])
    target_width, target_height = (int(value) for value in target["size_px"])
    cam_config = CameraConfig(
        viewport_width=width, viewport_height=height, fov_x_deg=fov_x, fov_y_deg=fov_y,
        update_rate_hz=float(camera["update_hz"]), max_pan_speed_deg_s=pan_rate,
        max_tilt_speed_deg_s=tilt_rate,
        max_acceleration_deg_s2=float(camera.get("max_acceleration_deg_s2", 25.0)),
    )
    env_config = EnvironmentConfig(
        screen_width=int(world["size_px"][0]), screen_height=int(world["size_px"][1]),
        star_count=int(world.get("star_count", 250)), random_seed=scenario.seed,
    )
    terminal_world_config = TerminalWorldConfig(
        nominal_range_m=float(world.get("nominal_range_m", 1000.0)),
        receiver_position_m=tuple(float(value) for value in world.get("receiver_position_m", [0, 0, 0])),
        receiver_velocity_m_s=tuple(float(value) for value in world.get("receiver_velocity_m_s", [0, 0, 0])),
        receiver_orientation_deg=tuple(float(value) for value in world.get("receiver_orientation_deg", [0, 0, 0])),
    )
    initial_x, initial_y = _target_position(target, world, camera)
    target_config = TargetConfig(
        shape=TargetShape(target["shape"]), size=round((target_width + target_height) / 2),
        trajectory=MotionTrajectory(target["trajectory"]), speed=float(target["speed_px_s"]),
        intensity=float(target.get("intensity", 255.0)), random_seed=scenario.seed,
        initial_x=initial_x, initial_y=initial_y,
        range_m=float(target["range_m"]) if target.get("range_m") is not None else None,
        orientation_deg=(
            tuple(float(value) for value in target["orientation_deg"])
            if target.get("orientation_deg") is not None else None
        ),
    )
    atmosphere = AtmosphericCondition(disturbance.get("atmosphere", "Clear"))
    platform = PlatformMotionType(disturbance.get("platform_motion", "None"))
    dropout = disturbance.get("dropout", {})
    disturb_config = DisturbanceConfig(
        random_seed=scenario.seed,
        enable_salt_pepper=float(disturbance.get("salt_pepper_fraction", 0)) > 0,
        salt_pepper_ratio=float(disturbance.get("salt_pepper_fraction", 0)),
        enable_gaussian_noise=float(disturbance.get("gaussian_noise_std", 0)) > 0,
        gaussian_noise_std=float(disturbance.get("gaussian_noise_std", 0)),
        enable_camera_jitter=float(disturbance.get("camera_jitter_max_px", 0)) > 0,
        max_camera_jitter_px=float(disturbance.get("camera_jitter_max_px", 0)),
        atmospheric_condition=atmosphere,
        atmospheric_severity=float(disturbance.get("atmosphere_strength", 0)),
        turbulence_warp_px=float(disturbance.get("turbulence_warp_px", 0)),
        turbulence_blur_sigma_px=float(disturbance.get("turbulence_blur_sigma_px", 0)),
        scintillation_log_std=float(disturbance.get("scintillation_log_std", 0)),
        illumination_flicker_fraction=float(disturbance.get("illumination_flicker_fraction", 0)),
        illumination_flicker_hz=float(disturbance.get("illumination_flicker_hz", 3)),
        enable_platform_motion=platform != PlatformMotionType.NONE,
        platform_motion_type=platform,
        platform_motion_amplitude_px=float(disturbance.get("platform_motion_max_px", 0)),
        dropout_enabled=bool(dropout.get("enabled", False)),
        dropout_start_s=float(dropout.get("start_s", 0)),
        dropout_duration_s=float(dropout.get("duration_s", 0)),
        dropout_burst_enabled=bool(dropout.get("burst_enabled", False)),
        dropout_mean_clear_s=float(dropout.get("mean_clear_s", 8.0)),
        dropout_mean_loss_s=float(dropout.get("mean_loss_s", 0.25)),
    )
    ctrl_config = ControllerConfig(
        coast_timeout_s=float(controller.get("coast_timeout_s", 0.4)),
        local_reacquire_timeout_s=float(controller.get("local_reacquire_timeout_s", 0.6)),
        latency_compensation_s=float(controller.get("latency_compensation_s", 0.0)),
    )
    code_lock = detector.get("code_lock") or {}
    det_config = DetectorConfig(
        algorithm=TrackingAlgorithm[str(detector.get("algorithm", "HYBRID")).upper()],
        code_lock_pattern=code_lock.get("pattern"),
        code_lock_symbol_frames=int(code_lock.get("symbol_frames", 1)),
        code_lock_minimum_correlation=float(code_lock.get("minimum_correlation", 0.70)),
        kalman_gate_threshold_chi2=float(detector.get("innovation_gate_chi2", 10000.0)),
    )
    tracker = TrackingSystem(
        cam_config, env_config, target_config, disturb_config, ctrl_config, det_config,
        terminal_world_config,
    )
    for decoy_data in configured_targets[1:]:
        decoy_x, decoy_y = _target_position(decoy_data, world, camera)
        decoy_width, decoy_height = (int(value) for value in decoy_data["size_px"])
        tracker.spawn_decoy(
            decoy_x, decoy_y,
            shape=TargetShape(decoy_data["shape"]),
            size=round((decoy_width + decoy_height) / 2),
            speed=float(decoy_data["speed_px_s"]),
            trajectory=MotionTrajectory(decoy_data["trajectory"]),
            intensity=float(decoy_data.get("intensity", 220.0)),
            random_seed=scenario.seed,
            range_m=(
                float(decoy_data["range_m"])
                if decoy_data.get("range_m") is not None else None
            ),
            orientation_deg=(
                tuple(float(value) for value in decoy_data["orientation_deg"])
                if decoy_data.get("orientation_deg") is not None else None
            ),
        )
    return tracker


def _target_position(target: Mapping[str, Any], world: Mapping[str, Any], camera: Mapping[str, Any]) -> tuple[float, float]:
    if "initial_position_px" in target:
        return float(target["initial_position_px"][0]), float(target["initial_position_px"][1])
    world_width, world_height = (float(value) for value in world["size_px"])
    view_width, view_height = (float(value) for value in camera["viewport_px"])
    centre_x, centre_y = world_width / 2.0, world_height / 2.0
    margin_x = max(10.0, view_width / 2.0 - 25.0)
    margin_y = max(10.0, view_height / 2.0 - 25.0)
    locations = {
        "center": (centre_x, centre_y),
        "left": (centre_x - margin_x, centre_y),
        "right": (centre_x + margin_x, centre_y),
        "top": (centre_x, centre_y - margin_y),
        "bottom": (centre_x, centre_y + margin_y),
        "top_left": (centre_x - margin_x, centre_y - margin_y),
        "top_right": (centre_x + margin_x, centre_y - margin_y),
        "bottom_left": (centre_x - margin_x, centre_y + margin_y),
        "bottom_right": (centre_x + margin_x, centre_y + margin_y),
    }
    label = str(target.get("initial_location", "center")).lower()
    if label not in locations:
        raise ScenarioError(f"target.initial_location is not supported: {label}")
    return locations[label]
