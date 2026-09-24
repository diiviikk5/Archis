"""Command-line workflows for simulation, recordings and SIH evidence reports."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import hashlib


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="archis", description="Archis FSOC tracking laboratory")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "simulate", "track", "record", "benchmark", "compare", "stress-test", "velocity-envelope"):
        item = commands.add_parser(name)
        item.add_argument("scenario", help="scenario or legacy preset JSON")
        if name in {"simulate", "track", "record", "benchmark"}:
            item.add_argument("--frames", type=int, default=0, help="zero uses scenario duration")
        if name in {"simulate", "track", "benchmark", "compare", "stress-test", "velocity-envelope"}:
            item.add_argument("--output-dir", default=f"reports/{name}")
        if name == "velocity-envelope":
            item.add_argument("--frames", type=int, default=300, help="frames evaluated per speed")
        if name == "record":
            item.add_argument("output", help="output MP4")
    analyze = commands.add_parser("analyze")
    analyze.add_argument("input", help="MP4, image, or image directory")
    analyze.add_argument("--truth", help="CSV or JSON centroid ground-truth sidecar")
    analyze.add_argument("--interpolate-truth", action="store_true")
    analyze.add_argument("--fps", type=float, default=30.0)
    analyze.add_argument(
        "--fov-deg", type=float, nargs=2, metavar=("HORIZONTAL", "VERTICAL"),
        help="camera FOV used to report optional angular errors in microradians",
    )
    analyze.add_argument("--max-frames", type=int, default=0)
    analyze.add_argument("--output-dir", default="reports/analysis")
    train = commands.add_parser("train-ai")
    train.add_argument("--samples", type=int, default=400)
    train.add_argument("--seed", type=int, default=26169)
    train.add_argument("--output", help="calibration JSON (defaults to writable Archis application data)")
    optics = commands.add_parser("validate-optics")
    optics.add_argument("--seed", type=int, default=26169)
    optics.add_argument("--output-dir", default="reports/optical-validation")
    geometry = commands.add_parser("validate-geometry")
    geometry.add_argument("--output-dir", default="reports/geometry-validation")
    robustness = commands.add_parser("validate-detector")
    robustness.add_argument("--seed", type=int, default=26169)
    robustness.add_argument("--algorithm", choices=("hybrid", "iwc", "gaussian"), default="hybrid")
    robustness.add_argument("--output-dir", default="reports/detector-validation")
    commands.add_parser("gui")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "gui":
        return _gui()
    if args.command == "analyze":
        return _analyze(args)
    if args.command == "train-ai":
        return _calibrate_ai(args)
    if args.command == "validate-optics":
        from .core.validation import write_optical_validation
        if args.seed < 0:
            print("Input error: --seed cannot be negative", file=sys.stderr)
            return 2
        paths = write_optical_validation(args.output_dir, seed=args.seed)
        for kind, path in paths.items():
            print(f"{kind.upper()}: {path}")
        return 0
    if args.command == "validate-geometry":
        from .core.demo_evidence import write_geometry_validation
        paths = write_geometry_validation(args.output_dir)
        for kind, path in paths.items():
            print(f"{kind.upper()}: {path}")
        return 0
    if args.command == "validate-detector":
        from .core.config import TrackingAlgorithm
        from .core.demo_evidence import write_detector_robustness
        if args.seed < 0:
            print("Input error: --seed cannot be negative", file=sys.stderr)
            return 2
        algorithms = {
            "hybrid": TrackingAlgorithm.HYBRID,
            "iwc": TrackingAlgorithm.IWC,
            "gaussian": TrackingAlgorithm.GAUSSIAN_FIT,
        }
        paths = write_detector_robustness(
            args.output_dir, seed=args.seed, algorithm=algorithms[args.algorithm]
        )
        for kind, path in paths.items():
            print(f"{kind.upper()}: {path}")
        return 0
    from .core.scenario import ScenarioError, load_scenario
    try:
        scenario = load_scenario(args.scenario)
    except ScenarioError as exc:
        print(f"Scenario error: {exc}", file=sys.stderr)
        return 2
    if args.command == "validate":
        print(json.dumps(scenario.data, indent=2))
        return 0
    if args.command == "simulate":
        return _simulate(scenario, args)
    if args.command == "track":
        return _benchmark(scenario, args, export_preview=True)
    if args.command == "record":
        return _record(scenario, args)
    if args.command == "benchmark":
        return _benchmark(scenario, args)
    if args.command == "compare":
        return _compare(scenario, args)
    if args.command == "stress-test":
        return _stress(scenario, args)
    if args.command == "velocity-envelope":
        from .core.validation import write_velocity_envelope
        try:
            paths = write_velocity_envelope(scenario, args.output_dir, frames=args.frames)
        except ValueError as exc:
            print(f"Input error: {exc}", file=sys.stderr)
            return 2
        for kind, path in paths.items():
            print(f"{kind.upper()}: {path}")
        return 0
    return 2


def _frame_count(scenario, requested: int) -> int:
    if requested < 0:
        raise ValueError("frame count cannot be negative")
    return requested or round(scenario.duration_s * float(scenario.data["camera"]["update_hz"]))


def _run_scenario(scenario, frames: int):
    from .core.performance import PerformanceRecorder
    from .core.scenario import tracker_from_scenario
    tracker = tracker_from_scenario(scenario)
    width, height = (int(value) for value in scenario.data["camera"]["viewport_px"])
    fps = float(scenario.data["camera"]["update_hz"])
    recorder = PerformanceRecorder(
        scenario.name, (width, height),
        fov_deg=tuple(float(value) for value in scenario.data["camera"]["fov_deg"]),
        configuration=dict(scenario.data),
        model_metadata=_model_metadata(tracker),
    )
    for _ in range(frames):
        tracker.step(1.0 / fps)
        recorder.record(tracker.last_result, tracker.last_truth, fps)  # type: ignore[arg-type]
    return tracker, recorder


def _simulate(scenario, args) -> int:
    import cv2
    frames = _frame_count(scenario, args.frames)
    tracker, _ = _run_scenario(scenario, frames)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / "simulation_preview.png"
    cv2.imwrite(str(path), tracker.current_frame)
    print(f"Rendered {frames} deterministic frames; preview: {path}")
    return 0


def _benchmark(scenario, args, export_preview: bool = False) -> int:
    import cv2
    frames = _frame_count(scenario, args.frames)
    tracker, recorder = _run_scenario(scenario, frames)
    paths = recorder.export(args.output_dir)
    summary = recorder.summary()
    if export_preview:
        cv2.imwrite(str(Path(args.output_dir) / "tracking_preview.png"), tracker.current_frame)
    print(json.dumps(summary.__dict__ if hasattr(summary, "__dict__") else __import__("dataclasses").asdict(summary), indent=2))
    for kind, path in paths.items():
        print(f"{kind.upper()}: {path}")
    return 0 if summary.passed else 1


def _record(scenario, args) -> int:
    import cv2
    from .core.scenario import tracker_from_scenario
    frames = _frame_count(scenario, args.frames)
    tracker = tracker_from_scenario(scenario)
    width, height = (int(value) for value in scenario.data["camera"]["viewport_px"])
    fps = float(scenario.data["camera"]["update_hz"])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height), True)
    if not writer.isOpened():
        print(f"Could not create MP4: {output}", file=sys.stderr); return 1
    try:
        for _ in range(frames):
            tracker.step(1.0 / fps)
            writer.write(cv2.cvtColor(tracker.current_frame, cv2.COLOR_GRAY2BGR))
    finally:
        writer.release()
    print(f"Recorded {frames} frames to {output}")
    return 0


def _analyze(args) -> int:
    from .core.performance import PerformanceRecorder
    from .core.sources import FrameSourceError, open_frame_source
    from .core.tracker import TrackingSystem
    from .core.truth import TruthSidecar, TruthSidecarError
    if args.fov_deg and not all(0.0 < value < 180.0 for value in args.fov_deg):
        print("Input error: both FOV values must be between 0 and 180 degrees", file=sys.stderr)
        return 2
    try:
        source = open_frame_source(args.input, args.fps)
        truth = TruthSidecar.load(args.truth) if args.truth else None
    except (FrameSourceError, TruthSidecarError) as exc:
        print(f"Input error: {exc}", file=sys.stderr); return 2
    tracker = TrackingSystem()
    recorder = None
    processed = 0
    try:
        while args.max_frames == 0 or processed < args.max_frames:
            frame = source.read()
            if frame is None: break
            sample = truth.sample_for(frame.index, frame.timestamp_s, interpolate=args.interpolate_truth) if truth else None
            result = tracker.process_packet(frame, sample)
            if recorder is None:
                height, width = frame.image.shape[:2]
                recorder = PerformanceRecorder(
                    Path(args.input).stem, (width, height),
                    fov_deg=tuple(args.fov_deg) if args.fov_deg else None,
                    configuration={
                        "input": str(args.input),
                        "camera": {
                            "native_resolution_px": [width, height],
                            "fov_deg": list(args.fov_deg) if args.fov_deg else None,
                        },
                    },
                    model_metadata=_model_metadata(tracker),
                )
            recorder.record(result, sample, getattr(source, "fps", args.fps))
            processed += 1
    finally:
        source.close()
    if recorder is None:
        print("Input contains no decodable frames", file=sys.stderr); return 2
    paths = recorder.export(args.output_dir)
    print(json.dumps(__import__("dataclasses").asdict(recorder.summary()), indent=2))
    for kind, path in paths.items(): print(f"{kind.upper()}: {path}")
    return 0


def _compare(scenario, args) -> int:
    import csv
    from .core.contracts import FramePacket
    from .core.performance import PerformanceRecorder
    from .core.scenario import Scenario, validate_scenario
    algorithms = ("HYBRID", "GAUSSIAN_FIT", "IWC", "AI_ONNX")
    variants = {}
    recorders = {}
    output = Path(args.output_dir); output.mkdir(parents=True, exist_ok=True)
    for algorithm in algorithms:
        data = deepcopy(dict(scenario.data)); data["detector"]["algorithm"] = algorithm
        variant = Scenario(validate_scenario(data), scenario.path)
        from .core.scenario import tracker_from_scenario
        variants[algorithm] = tracker_from_scenario(variant)
        width, height = (int(value) for value in variant.data["camera"]["viewport_px"])
        recorders[algorithm] = PerformanceRecorder(
            f"{scenario.name} - {algorithm}", (width, height),
            fov_deg=tuple(float(value) for value in variant.data["camera"]["fov_deg"]),
            configuration={**dict(variant.data), "comparison_input": "shared_hybrid_closed_loop_frames"},
            model_metadata=_model_metadata(variants[algorithm]),
        )

    # Generate each sensor frame exactly once, then give the same immutable
    # pixels and truth sample to every candidate algorithm. This prevents
    # algorithm-specific camera motion or random draws from changing the A/B
    # input stream.
    from .core.scenario import tracker_from_scenario
    source = tracker_from_scenario(scenario)
    fps = float(scenario.data["camera"]["update_hz"])
    for index in range(_frame_count(scenario, 0)):
        source.step(1.0 / fps)
        packet = FramePacket(
            index, index / fps, source.current_frame.copy(), "comparison",
            {"seed": scenario.seed, "scenario": scenario.name},
        )
        truth = source.last_truth
        for algorithm in algorithms:
            result = variants[algorithm].process_packet(packet, truth)
            recorders[algorithm].record(result, truth, fps)

    rows = []
    for algorithm in algorithms:
        recorder = recorders[algorithm]
        summary = __import__("dataclasses").asdict(recorder.summary())
        summary["algorithm"] = algorithm; rows.append(summary)
        recorder.export(output / algorithm.lower())
    with (output / "algorithm_comparison.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    (output / "algorithm_comparison.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(json.dumps(rows, indent=2)); return 0


def _stress(scenario, args) -> int:
    import csv
    from .core.scenario import Scenario, validate_scenario
    rows = []
    for noise in (0.0, 8.0, 16.0):
        for jitter in (0.0, 5.0, 10.0, 20.0):
            data = deepcopy(dict(scenario.data))
            data["disturbances"]["gaussian_noise_std"] = noise
            data["disturbances"]["camera_jitter_max_px"] = jitter
            variant = Scenario(validate_scenario(data), scenario.path)
            _, recorder = _run_scenario(variant, min(180, _frame_count(variant, 0)))
            row = __import__("dataclasses").asdict(recorder.summary())
            row.update(noise_std=noise, jitter_px=jitter); rows.append(row)
    output = Path(args.output_dir); output.mkdir(parents=True, exist_ok=True)
    with (output / "stress_envelope.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    (output / "stress_envelope.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(json.dumps(rows, indent=2)); return 0


def _calibrate_ai(args) -> int:
    import cv2
    import numpy as np
    from .core.ai_detector import NanoSpotDetector
    if args.samples < 20:
        print("--samples must be at least 20", file=sys.stderr); return 2
    rng = np.random.default_rng(args.seed); detector = NanoSpotDetector(); scores = []
    labels = []
    yy, xx = np.ogrid[:64, :64]
    for index in range(args.samples):
        positive = index % 2 == 0
        image = rng.normal(15, 5, (64, 64))
        if positive:
            x, y = rng.uniform(12, 52, 2); sigma = rng.uniform(1.8, 4.0)
            image += rng.uniform(160, 235) * np.exp(-((xx-x)**2 + (yy-y)**2)/(2*sigma*sigma))
        elif index % 4 == 1:
            cv2.line(image, (32, 8), (32, 56), 220, 2)
        _, _, _, score, _, _ = detector.detect_spot(np.clip(image, 0, 255).astype(np.uint8), min_confidence=0.0)
        scores.append(float(score)); labels.append(positive)
    split = max(20, round(args.samples * 0.70))
    calibration = list(zip(scores[:split], labels[:split]))
    validation = list(zip(scores[split:], labels[split:]))
    thresholds = np.linspace(0, 1, 201)
    eligible = []
    for threshold in thresholds:
        fp = sum(score >= threshold and not label for score, label in calibration)
        negatives = max(1, sum(not label for _, label in calibration))
        positives = max(1, sum(label for _, label in calibration))
        recall = sum(score >= threshold and label for score, label in calibration) / positives
        if fp / negatives < 0.01:
            eligible.append((recall, float(threshold), fp / negatives))
    calibration_recall, threshold, calibration_false_lock = max(
        eligible, key=lambda item: (item[0], -item[1]), default=(0.0, 1.0, 0.0)
    )
    validation_negatives = max(1, sum(not label for _, label in validation))
    validation_positives = max(1, sum(label for _, label in validation))
    false_lock = sum(score >= threshold and not label for score, label in validation) / validation_negatives
    validation_recall = sum(score >= threshold and label for score, label in validation) / validation_positives
    payload = {
        "seed": args.seed, "samples": args.samples, "calibration_samples": len(calibration),
        "validation_samples": len(validation), "threshold": threshold,
        "calibration_false_lock_rate": calibration_false_lock,
        "calibration_recall": calibration_recall,
        "false_lock_rate": false_lock, "validation_recall": validation_recall,
        "target_false_lock_rate": 0.01,
        "target_met": false_lock < 0.01,
        "method": "deterministic 70/30 held-out synthetic calibration",
        "model": detector.status,
    }
    if args.output:
        output = Path(args.output)
    else:
        from .resources import user_data_dir
        output = user_data_dir() / "models" / "nanospot_calibration.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2)); return 0


def _gui() -> int:
    from PyQt6.QtWidgets import QApplication
    from .ui.main_window import MainWindow
    app = QApplication.instance() or QApplication(sys.argv[:1])
    window = MainWindow(); window.show()
    return app.exec()


def _model_metadata(tracker) -> dict[str, object]:
    detector = tracker.detector.ai_detector
    path = Path(detector.model_path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    metadata_path = path.with_suffix(".json")
    provenance = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
    calibration_path = path.with_name("nanospot_calibration.json")
    calibration = json.loads(calibration_path.read_text(encoding="utf-8")) if calibration_path.is_file() else {}
    return {
        "name": "NanoSpot-Net",
        "status": detector.status,
        "sha256": digest,
        "loaded": detector.is_loaded,
        "model_type": provenance.get("model_type"),
        "training_seed": provenance.get("training_seed"),
        "calibration_threshold": calibration.get("threshold"),
        "held_out_false_lock_rate": calibration.get("false_lock_rate"),
        "calibration_target_met": calibration.get("target_met"),
    }


if __name__ == "__main__":
    raise SystemExit(main())
