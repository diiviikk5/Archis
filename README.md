# Archis Optical Tracker 2.0

Archis is an AI-assisted virtual camera tracking laboratory for Smart India Hackathon problem statement 26169: coarse alignment of mobile free-space optical communication terminals.

It combines a polished PyQt/Fluent simulator with a deterministic tracking and evaluation engine. The default hybrid pipeline performs full-frame robust acquisition, NanoSpot refinement, compact candidate verification, temporal confirmation, optional CodeLock identity checks, Kalman tracking, and bounded pan/tilt control.

## What is included

- Configurable 2000×2000 virtual world, beacon shapes and trajectories.
- Fixed-step, seeded noise, atmosphere, platform motion, jitter, and timed dropout.
- Explicit `SEARCH → ACQUIRE → TRACK → COAST → REACQUIRE` state machine.
- Hybrid, IWC, Gaussian-fit, NCC, and NanoSpot algorithm modes.
- Native-resolution MP4, still-image, and image-sequence analysis.
- Exact CSV/JSON ground-truth sidecars, with opt-in timestamp interpolation.
- Separate centroid error and camera pointing error—ground truth is never exposed to the detector, tracker, or controller.
- Per-frame CSV, machine-readable JSON, and self-contained HTML reports.
- Reproducible benchmark, algorithm comparison, stress sweep, and AI calibration commands.
- PyInstaller one-folder Windows build plus portable ZIP and Inno Setup installer workflow.

## Quick start

Python 3.11 x64 is the reference environment.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
archis gui
```

On Linux or macOS, activate with `source .venv/bin/activate`. Source execution is supported; Windows 11 x64 is the packaged-release target.

## Command line

```text
archis validate scenarios/schema_v2_example.json
archis simulate archis_tracker/presets/nominal_leo.json --frames 300
archis benchmark archis_tracker/presets/cloud_dropout.json --frames 1800 --output-dir reports/dropout
archis compare archis_tracker/presets/nominal_leo.json --output-dir reports/compare
archis stress-test archis_tracker/presets/heavy_turbulence.json --output-dir reports/stress
archis analyze input.mp4 --truth truth.csv --output-dir reports/video
archis train-ai --samples 400 --seed 26169
```

`track` adds a final frame preview, `record` creates a simulated MP4, and `gui` launches the desktop application. Run `archis --help` or `archis <command> --help` for all options.

## Truth sidecars

CSV rows require `frame_index` or `timestamp_s`, plus `x_px` and `y_px`. `visible` and `target_id` are optional. JSON accepts either an array of equivalent objects or `{ "frames": [...] }`.

Exact frame lookup is the default. Pass `--interpolate-truth` only when timestamp interpolation is desired. Missing or invisible truth is retained in logs but excluded from geometric accuracy metrics. Without a sidecar, reports are labelled `observed_tracking` and do not claim accuracy.

See [`scenarios/example_truth.csv`](scenarios/example_truth.csv) and [`scenarios/schema_v2_example.json`](scenarios/schema_v2_example.json).

## Architecture

```text
FrameSource ──> FramePacket ──> robust proposals ──> hybrid evidence
                                     │                    │
                                     │              identity / association
                                     │                    │
truth source ──> evaluator only      └──────────────> state machine
                                                           │
                                               Kalman + PID controller
                                                           │
                                              bounded virtual camera
```

Simulation applies effects in this order: world and targets, camera pose, platform motion/jitter, atmosphere/blur, sensor noise, then dropout. Sensor-space truth is calculated after geometry and sent only to visualization and evaluation.

## Current measured matrix

The latest verification run contains 15 runs: five 60-second, 30 Hz scenarios across seeds 26169–26171. These are development-machine measurements, not unseen-video guarantees. The CLI commands above regenerate the per-frame CSV, machine-readable JSON, and HTML evidence.

| Scenario | Acquisition | Centroid RMSE | Pointing RMSE | Worst loss | Reacquisition | Strict result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Nominal LEO | 0.10 s | 0.023–0.028 px | 2.86–2.89 px | 0.00% | n/a | Pass |
| Evasive target | 0.10 s | 0.027–0.029 px | 3.03–3.25 px | 0.00% | n/a | Pass |
| Heavy turbulence | 0.10 s | 0.247–0.253 px | 1.00 px | 0.00% | n/a | Pass |
| Cloud dropout | 0.10 s | 0.098–0.099 px | 0.961–0.965 px | 0.50% | 0.30 s | Pass |
| Platform jitter | 0.10 s | 0.025–0.036 px | 12.99–13.15 px | 0.00% | n/a | **Pointing gate miss** |

Twelve of the 15 strict runs passed; the three misses were all the platform-jitter pointing gate. Measured processing throughput ranged from 74.8 to 333.0 FPS on the development machine. Platform jitter demonstrates why centroid accuracy and closed-loop pointing accuracy are reported separately: detection remained accurate, but the camera offset exceeded the strict 10 px gate.

## Tests

```powershell
python -m pytest -q
```

The unified suite currently contains 73 tests covering acquisition at the frame center/edges/corners, truth isolation, repeatability, state transitions, CodeLock, controller bounds, preset migration, native-resolution media, truth sidecars, metrics, headless UI startup, and report export.

## Windows release

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1
```

The script runs tests, creates the one-folder application, packages a portable ZIP, builds the installer when Inno Setup is available, and writes SHA-256 checksums and a release manifest. Keep every file in `dist\ArchisTracker` together. The executable is `dist\ArchisTracker\ArchisTracker.exe`.

## Provenance

Archis1 commit `06022f1` is the product baseline. Qlyraxis commit `2514c5d` is the engineering reference; unrelated Git histories were not merged. Existing Archis preset names and the Fluent desktop workflow remain authoritative.

The formal technical report and user manual are intentionally deferred to the final submission pass.
