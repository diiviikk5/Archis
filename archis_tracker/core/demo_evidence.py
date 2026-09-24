"""Reproducible, judge-facing geometric and detector evidence artifacts."""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import time

import cv2
import numpy as np

from .camera import VirtualCamera
from .config import CameraConfig, DetectorConfig, EnvironmentConfig, TargetConfig, TargetShape, TrackingAlgorithm
from .detector import BeaconDetector
from .target import TargetBeacon
from .world_model import TwoTerminalWorldModel


@dataclass(frozen=True, slots=True)
class GeometryCase:
    name: str
    camera_pan_deg: float
    camera_tilt_deg: float
    target_world_x: float
    target_world_y: float
    predicted_x_px: float
    predicted_y_px: float
    measured_x_px: float | None
    measured_y_px: float | None
    discrepancy_px: float | None
    expected_visible: bool
    rendered_visible: bool
    passed: bool


def run_geometry_validation() -> tuple[list[GeometryCase], list[np.ndarray]]:
    """Compare independent pixel measurements with angular-plane projection.

    The 3D terminal layer maps to this angular plane; this check tests the
    renderer and camera projection, not a hardware optical calibration.
    """
    camera_config = CameraConfig()
    environment = EnvironmentConfig()
    camera = VirtualCamera(camera_config, environment)
    target = TargetBeacon(1, TargetConfig(shape=TargetShape.SQUARE, size=7,
                                          intensity=255, initial_x=1000, initial_y=1000))
    world = TwoTerminalWorldModel(camera_config, environment)
    cases = (
        ("center", 0.0, 0.0, 320.0, 240.0),
        ("left edge", 0.0, 0.0, 8.0, 240.0),
        ("right edge", 0.0, 0.0, 632.0, 240.0),
        ("top left corner", 0.0, 0.0, 8.0, 8.0),
        ("bottom right corner", 0.0, 0.0, 632.0, 472.0),
        ("outside FOV", 0.0, 0.0, -20.0, 240.0),
        ("pan 0.5 degree", 0.5, 0.0, 240.0, 240.0),
        ("tilt 0.3 degree", 0.0, 0.3, 320.0, 192.0),
    )
    rows: list[GeometryCase] = []
    frames: list[np.ndarray] = []
    for name, pan, tilt, desired_x, desired_y in cases:
        camera.pan_deg, camera.tilt_deg = pan, tilt
        camera.update_world_position()
        target.x = camera.world_x + desired_x - camera.width / 2.0
        target.y = camera.world_y + desired_y - camera.height / 2.0
        # Analytic angular-plane projection, evaluated from world and camera
        # pose rather than by calling the renderer's coordinate helper.
        azimuth_deg = (target.x - environment.screen_width / 2) / camera_config.pixels_per_deg_x
        elevation_deg = (target.y - environment.screen_height / 2) / camera_config.pixels_per_deg_y
        boresight_az_deg = (camera.world_x - environment.screen_width / 2) / camera_config.pixels_per_deg_x
        boresight_el_deg = (camera.world_y - environment.screen_height / 2) / camera_config.pixels_per_deg_y
        predicted_x = camera.width / 2 + (azimuth_deg - boresight_az_deg) * camera_config.pixels_per_deg_x
        predicted_y = camera.height / 2 + (elevation_deg - boresight_el_deg) * camera_config.pixels_per_deg_y
        expected_visible = 0 <= predicted_x < camera.width and 0 <= predicted_y < camera.height
        frame = np.full((camera.height, camera.width), 12, dtype=np.float32)
        target.render_onto_viewport(frame, camera.world_x, camera.world_y)
        image = np.clip(frame, 0, 255).astype(np.uint8)
        binary = (image >= 200).astype(np.uint8)
        moments = cv2.moments(binary, binaryImage=True)
        measured = (
            (moments["m10"] / moments["m00"], moments["m01"] / moments["m00"])
            if moments["m00"] else None
        )
        discrepancy = math.dist((predicted_x, predicted_y), measured) if measured else None
        snapshot = world.update(0.0, camera, target)
        passed = (expected_visible == (measured is not None)
                  and expected_visible == snapshot.transmitter_in_fov
                  and (discrepancy is None or discrepancy <= 0.75))
        rows.append(GeometryCase(
            name, pan, tilt, target.x, target.y, predicted_x, predicted_y,
            measured[0] if measured else None, measured[1] if measured else None,
            discrepancy, expected_visible, measured is not None, passed,
        ))
        frames.append(image)
    return rows, frames


@dataclass(frozen=True, slots=True)
class RobustnessCase:
    name: str
    target_present: bool
    target_x_px: float | None
    target_y_px: float | None
    detected: bool
    selected_x_px: float | None
    selected_y_px: float | None
    centroid_error_px: float | None
    outcome: str
    response: float
    processing_time_ms: float


def _spot(shape: tuple[int, int], center: tuple[float, float], peak: float,
          fwhm: float = 7.0) -> np.ndarray:
    yy, xx = np.indices(shape)
    sigma = fwhm / 2.354820045
    return peak * np.exp(-((xx - center[0]) ** 2 + (yy - center[1]) ** 2) / (2 * sigma * sigma))


def run_detector_robustness(*, seed: int = 26169,
                            algorithm: TrackingAlgorithm = TrackingAlgorithm.HYBRID
                            ) -> tuple[list[RobustnessCase], list[np.ndarray]]:
    """Score cold, single-frame acquisition; decoy identity is not coded here."""
    if seed < 0:
        raise ValueError("seed cannot be negative")
    shape = (128, 128)
    truth = (80.0, 64.0)
    rng = np.random.default_rng(seed)
    cases: list[tuple[str, np.ndarray, tuple[float, float] | None]] = []

    def add(name: str, peak: float, *, center: tuple[float, float] | None = truth,
            noise: float = 0.0, blur: float = 0.0, decoy: bool = False) -> None:
        image = np.full(shape, 12.0)
        if center is not None:
            image += _spot(shape, center, peak)
        if decoy:
            image += _spot(shape, (30.0, 35.0), 255.0)
        if noise:
            image += rng.normal(0.0, noise, shape)
        image = np.clip(image, 0, 255).astype(np.uint8)
        if blur:
            image = cv2.GaussianBlur(image, (0, 0), blur)
        cases.append((name, image, center))

    add("clean", 240)
    add("near left edge", 240, center=(8.0, 64.0))
    add("near corner", 240, center=(8.0, 8.0))
    add("dim", 55)
    add("very low contrast", 28)
    add("noise sigma 8", 240, noise=8)
    add("noise sigma 25", 240, noise=25)
    add("noise sigma 40", 240, noise=40)
    add("blur sigma 2", 240, blur=2)
    add("blur sigma 4", 240, blur=4)
    add("saturated", 400)
    add("bright decoy", 180, decoy=True)
    add("decoy only", 0, center=None, decoy=True)
    add("blank", 0, center=None)

    rows: list[RobustnessCase] = []
    images: list[np.ndarray] = []
    detector = BeaconDetector(DetectorConfig(algorithm=algorithm))
    detector.detect(cases[0][1])  # One model/backend warm-up before timed cases.
    for name, image, center in cases:
        detector.target_template = None
        detector.spot_scale_px = float(detector.config.fallback_fwhm_px)
        started = time.perf_counter()
        result = detector.detect(image)
        latency_ms = (time.perf_counter() - started) * 1000.0
        error = math.dist((result.x, result.y), center) if result.detected and center else None
        correct = error is not None and error <= 6.0
        outcome = (
            "TP" if correct else "FN+FP" if center and result.detected else
            "FN" if center else "FP" if result.detected else "TN"
        )
        rows.append(RobustnessCase(
            name, center is not None, center[0] if center else None,
            center[1] if center else None, result.detected,
            result.x if result.detected else None,
            result.y if result.detected else None, error,
            outcome, float(result.confidence),
            latency_ms,
        ))
        images.append(image)
    return rows, images


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_geometry_validation(output_dir: str | Path) -> dict[str, Path]:
    rows, frames = run_geometry_validation()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "geometry_validation.json"
    csv_path = output / "geometry_validation.csv"
    png_path = output / "geometry_validation.png"
    data = [asdict(row) for row in rows]
    payload = {
        "schema_version": 1,
        "basis": "angular-plane projection versus measured rendered beacon pixels",
        "tolerance_px": 0.75,
        "passed": all(row.passed for row in rows),
        "cases": data,
    }
    _write_csv(csv_path, data)
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tile_w, tile_h, columns = 330, 205, 2
    canvas = np.full((math.ceil(len(rows) / columns) * tile_h + 48,
                      columns * tile_w, 3), (23, 29, 37), dtype=np.uint8)
    cv2.putText(canvas, "ARCHIS | CAMERA PROJECTION CHECK", (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX, .7, (230, 240, 245), 1, cv2.LINE_AA)
    for index, (row, frame) in enumerate(zip(rows, frames)):
        image = cv2.resize(frame, (256, 128), interpolation=cv2.INTER_NEAREST)
        tile = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        if row.expected_visible:
            x = round(row.predicted_x_px * 256 / frame.shape[1])
            y = round(row.predicted_y_px * 128 / frame.shape[0])
            cv2.drawMarker(tile, (x, y), (100, 220, 255), cv2.MARKER_CROSS, 9, 1)
        x0, y0 = (index % columns) * tile_w, 48 + (index // columns) * tile_h
        canvas[y0 + 22:y0 + 150, x0 + 37:x0 + 293] = tile
        label = f"{row.name}: {'PASS' if row.passed else 'FAIL'}"
        cv2.putText(canvas, label, (x0 + 15, y0 + 17), cv2.FONT_HERSHEY_SIMPLEX,
                    .48, (110, 240, 160) if row.passed else (80, 80, 255), 1, cv2.LINE_AA)
        measured = (
            f"({row.measured_x_px:.1f}, {row.measured_y_px:.1f})"
            if row.rendered_visible else "outside FOV"
        )
        cv2.putText(canvas,
                    f"Pred ({row.predicted_x_px:.1f}, {row.predicted_y_px:.1f})  Meas {measured}",
                    (x0 + 15, y0 + 173), cv2.FONT_HERSHEY_SIMPLEX,
                    .39, (180, 200, 215), 1, cv2.LINE_AA)
        cv2.putText(canvas,
                    f"Discrepancy {row.discrepancy_px:.3f} px" if row.discrepancy_px is not None else "No rendered beacon",
                    (x0 + 15, y0 + 191), cv2.FONT_HERSHEY_SIMPLEX,
                    .39, (180, 200, 215), 1, cv2.LINE_AA)
    if not cv2.imwrite(str(png_path), canvas):
        raise OSError(f"could not write {png_path}")
    return {"json": json_path, "csv": csv_path, "png": png_path}


def write_detector_robustness(output_dir: str | Path, *, seed: int = 26169,
                              algorithm: TrackingAlgorithm = TrackingAlgorithm.HYBRID
                              ) -> dict[str, Path]:
    rows, frames = run_detector_robustness(seed=seed, algorithm=algorithm)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "detector_robustness.json"
    csv_path = output / "detector_robustness.csv"
    png_path = output / "detector_robustness_gallery.png"
    data = [asdict(row) for row in rows]
    counts = {key: sum(key in row.outcome for row in rows) for key in ("TP", "FN", "FP", "TN")}
    payload = {
        "schema_version": 1,
        "seed": seed,
        "algorithm": algorithm.value,
        "scope": "cold single-frame detector acquisition; no CodeLock sequence or closed-loop control",
        "latency_basis": "measured wall time on the generating machine; hardware dependent",
        "matching_tolerance_px": 6.0,
        "counts": counts,
        "cases": data,
    }
    _write_csv(csv_path, data)
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tile_w, tile_h, columns = 290, 208, 4
    gallery = np.full((math.ceil(len(rows) / columns) * tile_h, columns * tile_w, 3),
                      (20, 25, 32), dtype=np.uint8)
    for index, (row, frame) in enumerate(zip(rows, frames)):
        x0, y0 = (index % columns) * tile_w, (index // columns) * tile_h
        image = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        image = cv2.resize(image, (128, 128), interpolation=cv2.INTER_NEAREST)
        gallery[y0 + 22:y0 + 150, x0 + 80:x0 + 208] = image
        color = (110, 240, 160) if row.outcome in ("TP", "TN") else (80, 95, 255)
        cv2.rectangle(gallery, (x0 + 79, y0 + 21), (x0 + 208, y0 + 150), color, 1)
        cv2.putText(gallery, row.name, (x0 + 10, y0 + 17), cv2.FONT_HERSHEY_SIMPLEX,
                    .42, (220, 230, 240), 1, cv2.LINE_AA)
        detail = row.outcome + (f"  error {row.centroid_error_px:.2f}px" if row.centroid_error_px is not None else "")
        cv2.putText(gallery, detail, (x0 + 10, y0 + 170), cv2.FONT_HERSHEY_SIMPLEX,
                    .4, color, 1, cv2.LINE_AA)
        cv2.putText(gallery, f"latency {row.processing_time_ms:.2f}ms (host)",
                    (x0 + 10, y0 + 190), cv2.FONT_HERSHEY_SIMPLEX,
                    .4, (155, 175, 195), 1, cv2.LINE_AA)
    if not cv2.imwrite(str(png_path), gallery):
        raise OSError(f"could not write {png_path}")
    return {"json": json_path, "csv": csv_path, "png": png_path}
