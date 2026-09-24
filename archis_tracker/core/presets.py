"""Validated mission preset loading and application."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .config import AtmosphericCondition, MotionTrajectory, PlatformMotionType, TargetShape


class PresetError(ValueError):
    """Raised when a preset cannot be safely applied."""


@dataclass(frozen=True)
class LoadedPreset:
    name: str
    description: str
    path: Path


def _number(section: Mapping[str, Any], key: str, low: float, high: float) -> float | None:
    if key not in section:
        return None
    value = section[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PresetError(f"{key} must be a number")
    value = float(value)
    if not low <= value <= high:
        raise PresetError(f"{key} must be between {low:g} and {high:g}")
    return value


def _boolean(section: Mapping[str, Any], key: str) -> bool | None:
    if key not in section:
        return None
    value = section[key]
    if not isinstance(value, bool):
        raise PresetError(f"{key} must be true or false")
    return value


def _enum(section: Mapping[str, Any], key: str, enum_type):
    if key not in section:
        return None
    try:
        return enum_type(section[key])
    except (TypeError, ValueError) as exc:
        choices = ", ".join(item.value for item in enum_type)
        raise PresetError(f"{key} must be one of: {choices}") from exc


def _section(data: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise PresetError(f"{name} must be an object")
    return value


def load_and_apply_preset(tracker, path: str | Path) -> LoadedPreset:
    """Validate an entire JSON preset, then atomically apply it to a tracker."""
    preset_path = Path(path)
    try:
        data = json.loads(preset_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PresetError(f"Could not read preset: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise PresetError(f"Invalid JSON at line {exc.lineno}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise PresetError("Preset root must be an object")

    target = _section(data, "target")
    camera = _section(data, "camera")
    disturbances = _section(data, "disturbances")
    dropout = _section(disturbances, "dropout")

    values = {
        "shape": _enum(target, "shape", TargetShape),
        "size": _number(target, "size", 5, 20),
        "trajectory": _enum(target, "trajectory", MotionTrajectory),
        "speed": _number(target, "speed", 0.1, 500),
        "intensity": _number(target, "intensity", 1, 255),
        "pan_speed": _number(camera, "max_pan_speed_deg_s", 0.1, 10),
        "tilt_speed": _number(camera, "max_tilt_speed_deg_s", 0.1, 10),
        "fov_x": _number(camera, "fov_x_deg", 0.1, 180),
        "fov_y": _number(camera, "fov_y_deg", 0.1, 180),
        "atmosphere": _enum(disturbances, "atmospheric_condition", AtmosphericCondition),
        "severity": _number(disturbances, "atmospheric_severity", 0, 1),
        "turbulence_warp": _number(disturbances, "turbulence_warp_px", 0, 50),
        "turbulence_blur": _number(disturbances, "turbulence_blur_sigma_px", 0, 20),
        "scintillation": _number(disturbances, "scintillation_log_std", 0, 1.5),
        "illumination_flicker": _number(disturbances, "illumination_flicker_fraction", 0, .95),
        "illumination_hz": _number(disturbances, "illumination_flicker_hz", 0, 100),
        "salt_pepper": _boolean(disturbances, "enable_salt_pepper"),
        "salt_pepper_ratio": _number(disturbances, "salt_pepper_ratio", 0, 0.15),
        "gaussian": _boolean(disturbances, "enable_gaussian_noise"),
        "gaussian_std": _number(disturbances, "gaussian_noise_std", 0, 20),
        "poisson": _boolean(disturbances, "enable_poisson_noise"),
        "jitter": _boolean(disturbances, "enable_camera_jitter"),
        "jitter_px": _number(disturbances, "max_camera_jitter_px", 0, 20),
        "platform": _boolean(disturbances, "enable_platform_motion"),
        "platform_type": _enum(disturbances, "platform_motion_type", PlatformMotionType),
        "platform_px": _number(disturbances, "platform_motion_amplitude_px", 0, 20),
        "platform_hz": _number(disturbances, "platform_motion_frequency_hz", 0, 100),
        "dropout_enabled": _boolean(dropout, "enabled"),
        "dropout_start": _number(dropout, "start_s", 0, 86400),
        "dropout_duration": _number(dropout, "duration_s", 0, 86400),
        "dropout_burst": _boolean(dropout, "burst_enabled"),
        "dropout_mean_clear": _number(dropout, "mean_clear_s", 0.001, 86400),
        "dropout_mean_loss": _number(dropout, "mean_loss_s", 0.001, 86400),
    }

    primary = tracker.primary_target
    for key in ("shape", "trajectory", "speed", "intensity"):
        if values[key] is not None:
            setattr(primary, key, values[key])
    if values["size"] is not None:
        primary.size = int(values["size"])

    for key, attr in (("fov_x", "fov_x_deg"), ("fov_y", "fov_y_deg")):
        if values[key] is not None:
            setattr(tracker.cam_config, attr, values[key])
    tracker.camera.set_rate_limits(values["pan_speed"], values["tilt_speed"])

    disturbance_map = {
        "atmosphere": "atmospheric_condition",
        "severity": "atmospheric_severity",
        "turbulence_warp": "turbulence_warp_px",
        "turbulence_blur": "turbulence_blur_sigma_px",
        "scintillation": "scintillation_log_std",
        "illumination_flicker": "illumination_flicker_fraction",
        "illumination_hz": "illumination_flicker_hz",
        "salt_pepper": "enable_salt_pepper",
        "salt_pepper_ratio": "salt_pepper_ratio",
        "gaussian": "enable_gaussian_noise",
        "gaussian_std": "gaussian_noise_std",
        "poisson": "enable_poisson_noise",
        "jitter": "enable_camera_jitter",
        "jitter_px": "max_camera_jitter_px",
        "platform": "enable_platform_motion",
        "platform_type": "platform_motion_type",
        "platform_px": "platform_motion_amplitude_px",
        "platform_hz": "platform_motion_frequency_hz",
        "dropout_enabled": "dropout_enabled",
        "dropout_start": "dropout_start_s",
        "dropout_duration": "dropout_duration_s",
        "dropout_burst": "dropout_burst_enabled",
        "dropout_mean_clear": "dropout_mean_clear_s",
        "dropout_mean_loss": "dropout_mean_loss_s",
    }
    for key, attr in disturbance_map.items():
        if values[key] is not None:
            setattr(tracker.disturb_config, attr, values[key])

    tracker.reset()
    return LoadedPreset(
        name=str(data.get("name") or preset_path.stem),
        description=str(data.get("description") or ""),
        path=preset_path,
    )
