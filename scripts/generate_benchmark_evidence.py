#!/usr/bin/env python3
"""Generate and verify the committed SIH benchmark evidence.

The matrix is intentionally regenerated from the current tracking engine.  A
source-tree fingerprint and a manifest make CI fail when runtime code changes
without a corresponding evidence refresh.
"""
from __future__ import annotations

import argparse
import csv
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from archis_tracker import __version__
from archis_tracker.cli import _run_scenario
from archis_tracker.core.performance import PerformanceRecorder
from archis_tracker.core.scenario import Scenario, load_scenario, validate_scenario


OUTPUT = ROOT / "docs" / "benchmarks" / "generated"
DOCS = ROOT / "docs" / "benchmarks"
SEEDS = (26169, 26170, 26171)
FRAMES = 1800
PRESETS = {
    "nominal_leo": ("nominal_leo.json", "Nominal LEO Pass Benchmark"),
    "evasive_target": ("evasive_target.json", "High-Speed Evasive Target Benchmark"),
    "heavy_turbulence": ("heavy_turbulence.json", "Heavy Atmospheric Turbulence Benchmark"),
    "cloud_dropout": ("cloud_dropout.json", "Cloud Dropout and Re-acquisition Benchmark"),
    "platform_jitter": ("platform_jitter.json", "Platform Vibration Benchmark"),
}
SCENARIO_DOCS = {
    "nominal_leo": "benchmark_nominal_leo_pass.md",
    "evasive_target": "benchmark_high_speed_evasive.md",
    "heavy_turbulence": "benchmark_dense_fog_stress.md",
    "cloud_dropout": "benchmark_cloud_dropout_relock.md",
    "platform_jitter": "benchmark_platform_vibration.md",
}
ALL_DOCS = tuple(SCENARIO_DOCS.values()) + (
    "benchmark_processing_fps_profile.md",
    "benchmark_sensor_noise_snr.md",
)


def _sha256_text(path: Path) -> str:
    # Normalize line endings so verification is stable on Windows runners.
    content = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def engine_fingerprint() -> str:
    """Fingerprint every input capable of changing benchmark results."""
    paths: list[Path] = [ROOT / "archis_tracker" / "__init__.py"]
    paths.extend(sorted((ROOT / "archis_tracker" / "core").rglob("*.py")))
    paths.extend(sorted((ROOT / "archis_tracker" / "models").glob("*")))
    paths.extend(sorted((ROOT / "archis_tracker" / "presets").glob("*.json")))
    digest = hashlib.sha256()
    for path in paths:
        if not path.is_file():
            continue
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        if path.suffix.lower() in {".py", ".json"}:
            payload = path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
        else:
            payload = path.read_bytes()
        digest.update(payload)
        digest.update(b"\0")
    return digest.hexdigest()


def _cpu_name() -> str:
    name = platform.processor().strip()
    cpuinfo = Path("/proc/cpuinfo")
    if not name and cpuinfo.is_file():
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("model name"):
                name = line.partition(":")[2].strip()
                break
    return name or os.environ.get("PROCESSOR_IDENTIFIER", "unknown")


def _git_head() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def provenance(fingerprint: str) -> dict[str, Any]:
    import cv2
    import numpy as np

    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "application_version": __version__,
        "engine_fingerprint": fingerprint,
        "git_head_when_generated": _git_head(),
        "benchmark_frames_per_run": FRAMES,
        "seeds": list(SEEDS),
        "host": {
            "cpu": _cpu_name(),
            "os": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "opencv": cv2.__version__,
        },
        "throughput_note": (
            "processing_fps and conservative_processing_fps are wall-clock and host-dependent; deterministic accuracy "
            "fingerprints do not include processing latency"
        ),
    }


def _variant(path: Path, seed: int, *, noise: float | None = None, jitter: float | None = None) -> Scenario:
    source = load_scenario(path)
    data = deepcopy(dict(source.data))
    data["evaluation"]["random_seed"] = seed
    data["evaluation"]["duration_s"] = FRAMES / float(data["camera"]["update_hz"])
    if noise is not None:
        data["disturbances"]["gaussian_noise_std"] = noise
    if jitter is not None:
        data["disturbances"]["camera_jitter_max_px"] = jitter
    return Scenario(validate_scenario(data), source.path)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _fmt_range(rows: list[dict[str, Any]], key: str, suffix: str = "") -> str:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    if not values:
        return "n/a"
    low, high = min(values), max(values)
    if key.endswith("_pct"):
        precision = 2
    elif key in {"processing_fps", "conservative_processing_fps"}:
        precision = 1
    else:
        precision = 3
    text = f"{low:.{precision}f}" if abs(high - low) < 10 ** (-precision) else f"{low:.{precision}f}–{high:.{precision}f}"
    return text + suffix


def _deterministic_status(rows: list[dict[str, Any]]) -> str:
    checks = ("acquisition_passed", "centroid_passed", "pointing_passed", "loss_passed", "reacquisition_passed")
    return "PASS" if all(bool(row[key]) for row in rows for key in checks) else "REVIEW REQUIRED"


def _marker(fingerprint: str) -> str:
    return f"<!-- generated-by: scripts/generate_benchmark_evidence.py engine-fingerprint: {fingerprint} -->"


def _scenario_doc(title: str, rows: list[dict[str, Any]], fingerprint: str, host: dict[str, str]) -> str:
    deterministic = _deterministic_status(rows)
    fps_passes = sum(bool(row["fps_passed"]) for row in rows)
    reacq = _fmt_range(rows, "maximum_reacquisition_s", " s")
    return f"""# {title}

{_marker(fingerprint)}

Generated from three 60-second runs (1,800 frames each) using seeds 26169–26171.

| Metric | SIH gate | Measured range | Result |
| --- | ---: | ---: | --- |
| Acquisition time | ≤ 2.0 s | {_fmt_range(rows, 'acquisition_time_s', ' s')} | {'PASS' if all(r['acquisition_passed'] for r in rows) else 'FAIL'} |
| Centroid RMSE | ≤ 10 px | {_fmt_range(rows, 'centroid_rmse_px', ' px')} | {'PASS' if all(r['centroid_passed'] for r in rows) else 'FAIL'} |
| Pointing RMSE | ≤ 10 px | {_fmt_range(rows, 'pointing_rmse_px', ' px')} | {'PASS' if all(r['pointing_passed'] for r in rows) else 'FAIL'} |
| Target loss | < 5% | {_fmt_range(rows, 'target_loss_pct', '%')} | {'PASS' if all(r['loss_passed'] for r in rows) else 'FAIL'} |
| Worst re-acquisition | ≤ 1.0 s when applicable | {reacq} | {'PASS' if all(r['reacquisition_passed'] for r in rows) else 'FAIL'} |
| Conservative throughput (1000 / p95 latency) | ≥ 20 FPS | {_fmt_range(rows, 'conservative_processing_fps', ' FPS')} | {fps_passes}/3 on this host |

Deterministic accuracy/control verdict: **{deterministic}**. Throughput is reported separately because it depends on the host. A scenario is not claimed as a universal strict pass from these development-machine timings.

Host: `{host['cpu']}` · `{host['os']}` · Python `{host['python']}` · NumPy `{host['numpy']}` · OpenCV `{host['opencv']}`.
"""


def _processing_doc(rows: list[dict[str, Any]], fingerprint: str, host: dict[str, str]) -> str:
    by_preset = {key: [row for row in rows if row["preset"] == key] for key in PRESETS}
    lines = []
    for key, preset_rows in by_preset.items():
        lines.append(
            f"| {PRESETS[key][1].removesuffix(' Benchmark')} | {_fmt_range(preset_rows, 'conservative_processing_fps', ' FPS')} | "
            f"{sum(bool(r['fps_passed']) for r in preset_rows)}/3 |"
        )
    all_fps = [float(row["conservative_processing_fps"]) for row in rows]
    return f"""# Processing Throughput Profile

{_marker(fingerprint)}

These are wall-clock measurements, not deterministic algorithm outputs. They must be regenerated on the designated Windows 11 x64 reference machine before a release claim is made.

| Scenario | Measured range | Runs meeting ≥20 FPS |
| --- | ---: | ---: |
{chr(10).join(lines)}

Across all 15 runs: minimum **{min(all_fps):.1f} FPS**, median **{statistics.median(all_fps):.1f} FPS**, maximum **{max(all_fps):.1f} FPS**. Heavy-turbulence throughput near 20 FPS is therefore explicitly treated as host-dependent, not a universal pass.

Host: `{host['cpu']}` · `{host['os']}` · Python `{host['python']}` · NumPy `{host['numpy']}` · OpenCV `{host['opencv']}`.
"""


def _noise_doc(rows: list[dict[str, Any]], fingerprint: str, host: dict[str, str]) -> str:
    lines = []
    for row in rows:
        lines.append(
            f"| {row['noise_std']:.0f} | {row['centroid_rmse_px']:.3f} px | {row['pointing_rmse_px']:.3f} px | "
            f"{row['target_loss_pct']:.2f}% | {row['conservative_processing_fps']:.1f} FPS |"
        )
    return f"""# Sensor Noise vs Centroiding Accuracy

{_marker(fingerprint)}

This deterministic sweep uses the nominal scenario, seed 26169, zero injected camera jitter, and 180 frames per level. `gaussian_noise_std` is sensor intensity standard deviation in 8-bit pixel units; it is not an unmeasured SNR claim.

| Gaussian noise σ | Centroid RMSE | Pointing RMSE | Target loss | Host throughput |
| ---: | ---: | ---: | ---: | ---: |
{chr(10).join(lines)}

Host throughput is informational and machine-dependent. Host: `{host['cpu']}` · `{host['os']}` · Python `{host['python']}` · NumPy `{host['numpy']}` · OpenCV `{host['opencv']}`.
"""


def generate() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    fingerprint = engine_fingerprint()
    prov = provenance(fingerprint)
    matrix: list[dict[str, Any]] = []
    generated_files: list[Path] = []

    for preset, (filename, _) in PRESETS.items():
        for seed in SEEDS:
            scenario = _variant(ROOT / "archis_tracker" / "presets" / filename, seed)
            print(f"running {preset} seed {seed} ({FRAMES} frames)", flush=True)
            _, recorder = _run_scenario(scenario, FRAMES)
            row = asdict(recorder.summary())
            row.update(preset=preset, seed=seed)
            matrix.append(row)
            # Keep full per-frame proof for the canonical seed; the matrix keeps
            # reproducible fingerprints and summaries for all 15 runs.
            if seed == SEEDS[0]:
                generated_files.extend(recorder.export(OUTPUT / preset).values())

    matrix_csv = OUTPUT / "benchmark_matrix.csv"
    matrix_json = OUTPUT / "benchmark_matrix.json"
    _write_csv(matrix_csv, matrix)
    matrix_json.write_text(
        json.dumps({"schema_version": 2, "provenance": prov, "matrix": matrix}, indent=2) + "\n",
        encoding="utf-8",
    )
    generated_files.extend((matrix_csv, matrix_json))

    noise_rows: list[dict[str, Any]] = []
    for noise in (0.0, 8.0, 16.0):
        scenario = _variant(
            ROOT / "archis_tracker" / "presets" / "nominal_leo.json",
            SEEDS[0], noise=noise, jitter=0.0,
        )
        print(f"running sensor-noise sweep sigma={noise:g} (180 frames)", flush=True)
        _, recorder = _run_scenario(scenario, 180)
        row = asdict(recorder.summary())
        row["noise_std"] = noise
        noise_rows.append(row)
    noise_csv = OUTPUT / "sensor_noise_sweep.csv"
    noise_json = OUTPUT / "sensor_noise_sweep.json"
    _write_csv(noise_csv, noise_rows)
    noise_json.write_text(json.dumps(noise_rows, indent=2) + "\n", encoding="utf-8")
    generated_files.extend((noise_csv, noise_json))

    provenance_path = OUTPUT / "provenance.json"
    provenance_path.write_text(json.dumps(prov, indent=2) + "\n", encoding="utf-8")
    generated_files.append(provenance_path)

    host = prov["host"]
    for preset, (_, title) in PRESETS.items():
        path = DOCS / SCENARIO_DOCS[preset]
        selected = [row for row in matrix if row["preset"] == preset]
        path.write_text(_scenario_doc(title, selected, fingerprint, host), encoding="utf-8")
        generated_files.append(path)
    processing_path = DOCS / "benchmark_processing_fps_profile.md"
    processing_path.write_text(_processing_doc(matrix, fingerprint, host), encoding="utf-8")
    generated_files.append(processing_path)
    noise_path = DOCS / "benchmark_sensor_noise_snr.md"
    noise_path.write_text(_noise_doc(noise_rows, fingerprint, host), encoding="utf-8")
    generated_files.append(noise_path)

    manifest = {
        "schema_version": 1,
        "engine_fingerprint": fingerprint,
        "files": {
            path.relative_to(ROOT).as_posix(): _sha256_text(path)
            for path in sorted(generated_files)
        },
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"generated {len(matrix)} matrix rows; engine fingerprint {fingerprint}", flush=True)


def verify() -> list[str]:
    errors: list[str] = []
    manifest_path = OUTPUT / "manifest.json"
    if not manifest_path.is_file():
        return ["benchmark manifest is missing; regenerate evidence"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    current = engine_fingerprint()
    if manifest.get("engine_fingerprint") != current:
        errors.append("engine fingerprint changed; regenerate benchmark evidence")
    for relative, expected in manifest.get("files", {}).items():
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"generated evidence is missing: {relative}")
        elif _sha256_text(path) != expected:
            errors.append(f"generated evidence was edited or is stale: {relative}")

    matrix_path = OUTPUT / "benchmark_matrix.json"
    if matrix_path.is_file():
        payload = json.loads(matrix_path.read_text(encoding="utf-8"))
        rows = payload.get("matrix", [])
        expected_runs = {(preset, seed) for preset in PRESETS for seed in SEEDS}
        found_runs = {(row.get("preset"), row.get("seed")) for row in rows}
        if len(rows) != 15 or found_runs != expected_runs:
            errors.append("benchmark matrix must contain exactly five presets across three fixed seeds")
        if any(row.get("frames") != FRAMES or row.get("accuracy_basis") != "ground_truth" for row in rows):
            errors.append("every matrix run must contain 1,800 truth-scored frames")
        if any(row.get("passed") is not True for row in rows):
            errors.append("every matrix run must pass the configured acquisition, accuracy, loss, reacquisition and FPS gates")

    for preset in PRESETS:
        report_dir = OUTPUT / preset
        csv_paths = list(report_dir.glob("*_performance.csv"))
        json_paths = list(report_dir.glob("*_performance.json"))
        if len(csv_paths) != 1 or len(json_paths) != 1:
            errors.append(f"{preset} must contain one canonical CSV and JSON report")
            continue
        with csv_paths[0].open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            count = sum(1 for _ in reader)
            if tuple(reader.fieldnames or ()) != PerformanceRecorder.FIELDNAMES:
                errors.append(f"{preset} CSV uses a stale per-frame schema")
            if count != FRAMES:
                errors.append(f"{preset} CSV must contain {FRAMES} frames")
        report = json.loads(json_paths[0].read_text(encoding="utf-8"))
        if report.get("schema_version") != 2 or len(report.get("frames", [])) != FRAMES:
            errors.append(f"{preset} JSON report is incomplete or uses a stale schema")

    marker = _marker(current)
    for filename in ALL_DOCS:
        path = DOCS / filename
        if not path.is_file() or marker not in path.read_text(encoding="utf-8"):
            errors.append(f"benchmark document is not generated from the current engine: {filename}")
    return errors


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="verify evidence without running benchmarks")
    args = parser.parse_args(argv)
    if args.verify:
        errors = verify()
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print("benchmark evidence is complete and current")
        return 0
    generate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
