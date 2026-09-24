"""Deterministic optical-quality and velocity-envelope validation workflows."""
from __future__ import annotations

import csv
from copy import deepcopy
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np

from .config import AGCMode, DetectorConfig, TrackingAlgorithm
from .detector import BeaconDetector


@dataclass(frozen=True, slots=True)
class OpticalValidationRow:
    requested_fwhm_px: float
    noise_std: float
    requested_peak: float
    phase_x: float
    phase_y: float
    detected: bool
    centroid_error_px: float | None
    measured_fwhm_px: float | None
    snr_aperture: float | None
    snr_peak: float | None
    clipped: bool
    saturated_fraction: float


def _synthetic_spot(fwhm_px: float, noise_std: float, peak: float,
                    phase_xy: tuple[float, float], seed: int) -> tuple[np.ndarray, tuple[float, float]]:
    rng = np.random.default_rng(seed)
    height = width = 128
    center = (64.0 + phase_xy[0], 64.0 + phase_xy[1])
    yy, xx = np.indices((height, width), dtype=np.float64)
    sigma = fwhm_px / 2.354820045
    image = 12.0 + peak * np.exp(
        -((xx - center[0]) ** 2 + (yy - center[1]) ** 2) / (2.0 * sigma * sigma)
    )
    if noise_std > 0:
        image += rng.normal(0.0, noise_std, image.shape)
    return np.clip(image, 0.0, 255.0).astype(np.uint8), center


def run_optical_validation(*, seed: int = 26169,
                           fwhm_values: Iterable[float] = (3.0, 7.0, 15.0),
                           noise_values: Iterable[float] = (1.0, 6.0, 14.0),
                           peak_values: Iterable[float] = (120.0, 240.0, 360.0),
                           phases: Iterable[tuple[float, float]] = ((.15, .35), (.65, .85))) -> list[OpticalValidationRow]:
    """Sweep spot size, sensor noise and saturation using fixed synthetic pixels."""
    rows: list[OpticalValidationRow] = []
    case = 0
    for fwhm in fwhm_values:
        for noise in noise_values:
            for peak in peak_values:
                for phase in phases:
                    frame, truth = _synthetic_spot(fwhm, noise, peak, phase, seed + case)
                    detector = BeaconDetector(DetectorConfig(
                        algorithm=TrackingAlgorithm.IWC,
                        agc_mode=AGCMode.LINEAR,
                        fallback_fwhm_px=float(fwhm),
                        minimum_fwhm_px=1.5,
                        maximum_fwhm_px=64.0,
                    ))
                    result = detector.detect(frame)
                    error = math.dist((result.x, result.y), truth) if result.detected else None
                    rows.append(OpticalValidationRow(
                        float(fwhm), float(noise), float(peak), float(phase[0]), float(phase[1]),
                        result.detected, error, result.fwhm_px, result.snr_aperture,
                        result.snr_peak, result.clipped, result.saturated_fraction,
                    ))
                    case += 1
    return rows


def calibrate_measurement_noise(rows: Iterable[OpticalValidationRow]) -> float:
    """Fit a conservative scale factor for sigma = k*FWHM/(2*SNR).

    The 95th percentile of normalized observed error is used so unusually
    favourable high-SNR cases cannot make the estimator overconfident.
    Saturated, clipped and missed detections are excluded from calibration.
    """
    factors = []
    for row in rows:
        if (
            row.detected and row.centroid_error_px is not None
            and row.measured_fwhm_px and row.snr_aperture
            and not row.clipped and row.saturated_fraction <= .05
        ):
            factors.append(
                2.0 * row.snr_aperture * row.centroid_error_px / row.measured_fwhm_px
            )
    if not factors:
        raise ValueError("no valid optical validation rows for calibration")
    return float(np.clip(np.percentile(factors, 95), 1.0, 20.0))


def write_optical_validation(output_dir: str | Path, *, seed: int = 26169) -> dict[str, Path]:
    rows = run_optical_validation(seed=seed)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    csv_path = output / "optical_validation_sweep.csv"
    json_path = output / "optical_validation_sweep.json"
    dictionaries = [asdict(row) for row in rows]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(dictionaries[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(dictionaries)
    payload = {
        "schema_version": 1,
        "seed": seed,
        "measurement_noise_model": "sigma_px = k * FWHM_px / (2 * aperture_SNR)",
        "recommended_calibration": calibrate_measurement_noise(rows),
        "rows": dictionaries,
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {"csv": csv_path, "json": json_path}


def mechanical_velocity_limit_px_s(scenario) -> float:
    camera = scenario.data["camera"]
    width, height = (float(value) for value in camera["viewport_px"])
    fov_x, fov_y = (float(value) for value in camera["fov_deg"])
    pan_rate, tilt_rate = (float(value) for value in camera["max_rate_deg_s"])
    return min(pan_rate * width / fov_x, tilt_rate * height / fov_y)


def run_velocity_envelope(scenario, *, speeds_px_s: Iterable[float] | None = None,
                          frames: int = 300) -> dict:
    """Measure tracking over a finite speed set bounded by gimbal mechanics."""
    from .scenario import Scenario, tracker_from_scenario, validate_scenario
    from .performance import PerformanceRecorder

    if frames <= 0:
        raise ValueError("frames must be positive")
    mechanical_limit = mechanical_velocity_limit_px_s(scenario)
    if speeds_px_s is None:
        speeds_px_s = tuple(mechanical_limit * ratio for ratio in (.05, .10, .20, .35, .50, .75, 1.0))
    speeds = sorted({float(speed) for speed in speeds_px_s if 0.0 <= float(speed) <= mechanical_limit})
    if not speeds:
        raise ValueError("no requested speeds are within the mechanical limit")
    rows = []
    for speed in speeds:
        data = deepcopy(dict(scenario.data))
        primary = data["targets"][0] if data.get("targets") else data["target"]
        primary["trajectory"] = "Straight Line"
        primary["speed_px_s"] = speed
        primary.pop("initial_position_px", None)
        primary["initial_location"] = "center"
        variant = Scenario(validate_scenario(data), scenario.path)
        tracker = tracker_from_scenario(variant)
        width, height = (int(value) for value in data["camera"]["viewport_px"])
        fps = float(data["camera"]["update_hz"])
        recorder = PerformanceRecorder(
            f"{scenario.name} velocity {speed:.3f}px_s", (width, height),
            fov_deg=tuple(float(value) for value in data["camera"]["fov_deg"]),
            configuration=data,
        )
        for _ in range(frames):
            tracker.step(1.0 / fps)
            recorder.record(tracker.last_result, tracker.last_truth, fps)
        summary = asdict(recorder.summary())
        trackable = bool(
            summary["acquisition_passed"] and summary["centroid_passed"]
            and summary["pointing_passed"] and summary["loss_passed"]
        )
        rows.append({
            "speed_px_s": speed,
            "fraction_of_mechanical_limit": speed / mechanical_limit,
            "trackable": trackable,
            "centroid_rmse_px": summary["centroid_rmse_px"],
            "pointing_rmse_px": summary["pointing_rmse_px"],
            "target_loss_pct": summary["target_loss_pct"],
            "conservative_processing_fps": summary["conservative_processing_fps"],
        })
    passing = [row["speed_px_s"] for row in rows if row["trackable"]]
    return {
        "schema_version": 1,
        "mechanical_limit_px_s": mechanical_limit,
        "tested_maximum_px_s": max(speeds),
        "bounded_trackable_velocity_px_s": max(passing) if passing else None,
        "frames_per_speed": frames,
        "rows": rows,
    }


def write_velocity_envelope(scenario, output_dir: str | Path, *, frames: int = 300) -> dict[str, Path]:
    payload = run_velocity_envelope(scenario, frames=frames)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    csv_path = output / "velocity_envelope.csv"
    json_path = output / "velocity_envelope.json"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(payload["rows"][0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(payload["rows"])
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {"csv": csv_path, "json": json_path}
