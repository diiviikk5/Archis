"""Truth-aware per-frame metrics and reproducible CSV/JSON/HTML reports."""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import html
import hashlib
import json
import math
from pathlib import Path
from statistics import mean
from typing import Any

from archis_tracker import __version__

from .config import PerformanceThresholds
from .contracts import GroundTruthSample, TrackingResult
from .optics import PinholeCameraModel


@dataclass(frozen=True, slots=True)
class PerformanceSummary:
    scenario: str
    frames: int
    duration_s: float
    acquisition_time_s: float | None
    centroid_rmse_px: float | None
    centroid_mean_px: float | None
    centroid_max_px: float | None
    centroid_p95_px: float | None
    centroid_rmse_urad: float | None
    pointing_rmse_px: float | None
    pointing_rmse_urad: float | None
    lock_retention_pct: float
    target_loss_pct: float
    average_processing_ms: float
    processing_p50_ms: float
    processing_p95_ms: float
    maximum_processing_ms: float
    processing_fps: float
    conservative_processing_fps: float
    reacquisition_count: int
    average_reacquisition_s: float | None
    maximum_reacquisition_s: float | None
    accuracy_basis: str
    run_fingerprint: str
    acquisition_passed: bool
    centroid_passed: bool
    pointing_passed: bool
    loss_passed: bool
    reacquisition_passed: bool
    fps_passed: bool
    passed: bool


class PerformanceRecorder:
    FIELDNAMES = (
        "frame_index", "timestamp_s", "state", "detected", "selected_x_px", "selected_y_px",
        "truth_x_px", "truth_y_px", "truth_visible", "centroid_error_px", "pointing_offset_px",
        "centroid_error_urad", "pointing_offset_urad",
        "fwhm_px", "snr_aperture", "snr_peak", "clipped", "saturated_fraction",
        "measurement_sigma_px", "innovation_distance_sq",
        "pan_rate_deg_s", "tilt_rate_deg_s", "processing_time_ms", "source_fps",
    )

    def __init__(self, scenario: str, viewport_px: tuple[int, int], *,
                 fov_deg: tuple[float, float] | None = None,
                 configuration: dict[str, Any] | None = None,
                 model_metadata: dict[str, Any] | None = None,
                 thresholds: PerformanceThresholds | None = None) -> None:
        self.scenario = scenario
        self.viewport_px = viewport_px
        self.optics = (
            PinholeCameraModel(viewport_px[0], viewport_px[1], fov_deg[0], fov_deg[1])
            if fov_deg is not None else None
        )
        self.configuration = configuration or {}
        self.model_metadata = model_metadata or {}
        self.thresholds = thresholds or PerformanceThresholds()
        self.rows: list[dict[str, Any]] = []
        self.acquired_at: float | None = None
        self.loss_started_at: float | None = None
        self.reacquisition_times: list[float] = []
        self.previous_locked = False
        self._fingerprint = hashlib.sha256()

    def record(self, result: TrackingResult, truth: GroundTruthSample | None = None,
               source_fps: float = 30.0) -> None:
        if self.rows and result.frame.timestamp_s <= float(self.rows[-1]["timestamp_s"]):
            raise ValueError("frame timestamps must increase")
        selected = result.selected
        locked = result.state.value == "track" and selected is not None
        if locked and self.acquired_at is None:
            self.acquired_at = result.frame.timestamp_s
        if self.previous_locked and not locked and self.acquired_at is not None and self.loss_started_at is None:
            self.loss_started_at = result.frame.timestamp_s
        if locked and self.loss_started_at is not None:
            self.reacquisition_times.append(result.frame.timestamp_s - self.loss_started_at)
            self.loss_started_at = None
        self.previous_locked = locked
        scored_truth = truth if truth is not None and truth.visible else None
        centroid = math.dist((selected.x_px, selected.y_px), (scored_truth.x_px, scored_truth.y_px)) if selected and scored_truth else None
        pointing = math.dist((scored_truth.x_px, scored_truth.y_px), (self.viewport_px[0] / 2, self.viewport_px[1] / 2)) if scored_truth else None
        centroid_urad = (
            self.optics.angular_separation_urad(
                (selected.x_px, selected.y_px), (scored_truth.x_px, scored_truth.y_px)
            )
            if self.optics is not None and selected and scored_truth else None
        )
        pointing_urad = (
            self.optics.boresight_offset_urad(scored_truth.x_px, scored_truth.y_px)
            if self.optics is not None and scored_truth else None
        )
        self.rows.append({
            "frame_index": result.frame.index,
            "timestamp_s": result.frame.timestamp_s,
            "state": result.state.value,
            "detected": int(selected is not None),
            "selected_x_px": None if selected is None else selected.x_px,
            "selected_y_px": None if selected is None else selected.y_px,
            "truth_x_px": None if truth is None else truth.x_px,
            "truth_y_px": None if truth is None else truth.y_px,
            "truth_visible": None if truth is None else int(truth.visible),
            "centroid_error_px": centroid,
            "pointing_offset_px": pointing,
            "centroid_error_urad": centroid_urad,
            "pointing_offset_urad": pointing_urad,
            "fwhm_px": None if selected is None else selected.fwhm_px,
            "snr_aperture": None if selected is None else selected.snr_aperture,
            "snr_peak": None if selected is None else selected.snr_peak,
            "clipped": None if selected is None else int(selected.clipped),
            "saturated_fraction": None if selected is None else selected.saturated_fraction,
            "measurement_sigma_px": result.diagnostics.get("measurement_sigma_px"),
            "innovation_distance_sq": result.diagnostics.get("innovation_distance_sq"),
            "pan_rate_deg_s": None if result.command is None else result.command.pan_rate_deg_s,
            "tilt_rate_deg_s": None if result.command is None else result.command.tilt_rate_deg_s,
            "processing_time_ms": result.processing_time_ms,
            "source_fps": source_fps,
        })
        reproducible = {
            "frame_index": result.frame.index,
            "timestamp_s": round(result.frame.timestamp_s, 9),
            "state": result.state.value,
            "selected": None if selected is None else [round(selected.x_px, 6), round(selected.y_px, 6)],
            "truth": None if truth is None else [round(truth.x_px, 6), round(truth.y_px, 6), truth.visible, truth.target_id],
        }
        self._fingerprint.update(json.dumps(reproducible, sort_keys=True, separators=(",", ":")).encode())

    def summary(self) -> PerformanceSummary:
        if not self.rows:
            raise ValueError("cannot summarize an empty run")
        after = [row for row in self.rows if self.acquired_at is not None and float(row["timestamp_s"]) >= self.acquired_at]
        centroid = [float(row["centroid_error_px"]) for row in after if row["centroid_error_px"] is not None]
        pointing = [float(row["pointing_offset_px"]) for row in after if row["pointing_offset_px"] is not None]
        centroid_urad = [float(row["centroid_error_urad"]) for row in after if row["centroid_error_urad"] is not None]
        pointing_urad = [float(row["pointing_offset_urad"]) for row in after if row["pointing_offset_urad"] is not None]
        processing = [float(row["processing_time_ms"]) for row in self.rows]
        truth_available = any(row["truth_visible"] == 1 for row in self.rows)
        locked = sum(
            row["state"] == "track" and bool(row["detected"])
            and (not truth_available or (row["centroid_error_px"] is not None and float(row["centroid_error_px"]) <= self.thresholds.max_tracking_error_px))
            for row in after
        )
        retention = 100.0 * locked / len(after) if after else 0.0
        average_ms = mean(processing)
        p50_ms = _percentile(processing, .50)
        p95_ms = _percentile(processing, .95)
        centroid_rmse = math.sqrt(mean(value * value for value in centroid)) if centroid else None
        reacq_max = max(self.reacquisition_times) if self.reacquisition_times else None
        acquired = self.acquired_at is not None and self.acquired_at <= self.thresholds.max_acquisition_time_s
        centroid_pass = centroid_rmse is not None and centroid_rmse <= self.thresholds.max_tracking_error_px if truth_available else True
        pointing_rmse = math.sqrt(mean(value * value for value in pointing)) if pointing else None
        pointing_pass = pointing_rmse is not None and pointing_rmse <= self.thresholds.max_tracking_error_px if truth_available else True
        loss_pass = (100.0 - retention) < self.thresholds.max_target_loss_pct
        dropout = self.configuration.get("disturbances", {}).get("dropout", {})
        dropout_end = float(dropout.get("start_s", 0)) + float(dropout.get("duration_s", 0))
        reacq_expected = bool(dropout.get("enabled", False)) and dropout_end <= float(self.rows[-1]["timestamp_s"])
        reacq_pass = (
            reacq_max is not None and reacq_max <= self.thresholds.max_reacquisition_time_s
            if reacq_expected else
            reacq_max is None or reacq_max <= self.thresholds.max_reacquisition_time_s
        )
        fps = 1000.0 / average_ms if average_ms > 0 else 0.0
        conservative_fps = 1000.0 / p95_ms if p95_ms > 0 else 0.0
        fps_pass = conservative_fps >= self.thresholds.min_processing_fps
        return PerformanceSummary(
            self.scenario, len(self.rows), float(self.rows[-1]["timestamp_s"]) - float(self.rows[0]["timestamp_s"]),
            self.acquired_at, centroid_rmse, mean(centroid) if centroid else None,
            max(centroid) if centroid else None, _percentile(centroid, .95) if centroid else None,
            math.sqrt(mean(value * value for value in centroid_urad)) if centroid_urad else None,
            pointing_rmse,
            math.sqrt(mean(value * value for value in pointing_urad)) if pointing_urad else None,
            retention, 100.0 - retention, average_ms, p50_ms, p95_ms,
            max(processing), fps, conservative_fps,
            len(self.reacquisition_times), mean(self.reacquisition_times) if self.reacquisition_times else None,
            reacq_max, "ground_truth" if truth_available else "observed_tracking",
            self._fingerprint.hexdigest(),
            bool(acquired), bool(centroid_pass), bool(pointing_pass), bool(loss_pass),
            bool(reacq_pass), bool(fps_pass),
            bool(acquired and centroid_pass and pointing_pass and loss_pass and reacq_pass and fps_pass),
        )

    def export(self, output_dir: str | Path) -> dict[str, Path]:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        stem = "".join(char if char.isalnum() or char in "-_" else "_" for char in self.scenario).strip("_") or "archis"
        paths = {kind: output / f"{stem}_performance.{kind}" for kind in ("csv", "json", "html")}
        with paths["csv"].open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.FIELDNAMES, lineterminator="\n")
            writer.writeheader(); writer.writerows(self.rows)
        payload = {
            "schema_version": 2,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "application": {"name": "Archis Optical Tracker", "version": __version__},
            "model": self.model_metadata,
            "summary": asdict(self.summary()), "configuration": self.configuration,
            "thresholds": asdict(self.thresholds), "frames": self.rows,
        }
        paths["json"].write_text(json.dumps(payload, indent=2), encoding="utf-8")
        summary_rows = _html_rows(payload["summary"])
        threshold_rows = _html_rows(payload["thresholds"])
        model_rows = _html_rows(payload["model"])
        configuration = html.escape(json.dumps(payload["configuration"], indent=2))
        verdict = "PASS" if payload["summary"]["passed"] else "REVIEW REQUIRED"
        verdict_color = "#62d3a4" if payload["summary"]["passed"] else "#ffb45e"
        paths["html"].write_text(
            "<!doctype html><meta charset='utf-8'><title>Archis Performance Report</title>"
            "<style>body{font:15px system-ui;background:#071018;color:#e7eef5;max-width:960px;margin:40px auto}"
            "table{width:100%;border-collapse:collapse}th,td{padding:9px;border-bottom:1px solid #294052;text-align:left}"
            "th{color:#83d9ce;width:45%}pre{background:#0c1924;border:1px solid #294052;padding:16px;overflow:auto}"
            "h2{margin-top:32px}</style><h1>Archis FSOC Performance Report</h1>"
            f"<p>Version <strong>{html.escape(__version__)}</strong> · generated {html.escape(payload['generated_at_utc'])}</p>"
            f"<p style='color:{verdict_color};font-size:20px;font-weight:700'>{verdict}</p>"
            f"<p>Accuracy basis: <strong>{payload['summary']['accuracy_basis']}</strong></p>"
            f"<h2>Measured summary</h2><table>{summary_rows}</table>"
            f"<h2>Configured thresholds</h2><table>{threshold_rows}</table>"
            f"<h2>AI model provenance</h2><table>{model_rows}</table>"
            f"<h2>Scenario configuration</h2><pre>{configuration}</pre>",
            encoding="utf-8",
        )
        return paths


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _html_rows(values: dict[str, Any]) -> str:
    return "".join(
        f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>"
        for key, value in values.items()
    )
