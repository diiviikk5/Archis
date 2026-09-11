# Archis Desktop Application Overhaul

## Product Decision

Archis remains a Python Qt6 desktop application. OpenCV and NumPy frames stay in the
same process as detection, tracking, disturbance generation and display. PyQtGraph
renders telemetry without serializing image arrays across a web-runtime boundary.
PyInstaller is the initial packaging route; Nuitka is evaluated only after the product
workflow is complete and measured.

The overhaul is delivered sequentially. A phase closes only when its operator flow,
error states, tests and packaged behavior are verified. Every completed slice is
committed and pushed to `main`.

## Phase 0 - Truthful Baseline

Status: Complete

- [x] Record all problem-statement requirements and delivery gates.
- [x] Reject empty or missing benchmark evidence instead of reporting a pass.
- [x] Exercise acquisition, dropout and measured reacquisition in the benchmark.
- [x] Separate camera update rate from measured processing throughput.
- [x] Generate automatic CSV, JSON and readable reports for each run.
- [x] Replace broken preset buttons with validated live-engine configuration.

Exit evidence: 24 tests passed; 10-second benchmark measured acquisition, dropout,
reacquisition, loss, error and throughput; commits through `366df9b` are on `main`.

## Phase 1 - Desktop Shell and First Run

Status: Functional first pass; visual QA and operator testing remain

- [x] Start paused so the operator controls when a run begins.
- [x] Add persistent first-run onboarding with a one-click nominal mission path.
- [x] Add prominent Start/Pause, Reset, Quick Start and Open Reports actions.
- [x] Show the Configure, Acquire, Track and Review workflow across the application.
- [x] Reorganize mission controls, viewport, minimap, metrics and charts into a stable
  desktop workspace.
- [x] Add keyboard run controls (`Space`, `Ctrl+R`) and readable status messages.
- [ ] Add application icon, About dialog, version/build identity and crash recovery.
- [ ] Persist window layout, selected tab, last scenario and safe operator settings.
- [ ] Complete visual QA at 1120x720, 1440x900, 1920x1080 and Windows display scaling.

Exit gate: a new evaluator can launch, understand the workflow, run Nominal LEO,
pause/reset it and find the report without documentation or developer help.

## Phase 2 - Mission Setup That Cannot Lie

Status: In progress

- [x] Apply bundled presets to the live target, camera, gimbal and disturbance engines.
- [x] Validate target, camera and disturbance bounds before any preset mutation.
- [ ] Replace nested setup tabs with a guided mission editor: Source, Target, Camera,
  Environment, Tracking and Review.
- [ ] Expose all mandatory parameters: world size, camera resolution/FOV/rate, initial
  target position, target count/shape/size/motion, pan/tilt limits and update interval.
- [ ] Add numeric controls for Gaussian deviation, salt-and-pepper ratio, jitter,
  platform amplitude/frequency and atmospheric severity.
- [ ] Add field-level validation, units, defaults, reset-to-default and invalid-state
  explanations.
- [ ] Implement Save Mission and Open Mission using a versioned JSON schema.
- [ ] Add a preflight review that lists configured values and flags unsupported or
  contradictory combinations before Start.

Exit gate: every annexure parameter can be configured, saved, reopened and proven to
change the live engine; malformed files cannot partially alter a mission.

## Phase 3 - Optical Viewport and Target Operations

Status: Existing capabilities need workflow polish

- [x] Display the actual monochrome FPA frame, detection, prediction and boresight.
- [x] Designate a target and inject a decoy from the viewport or minimap.
- [ ] Add explicit viewport tools: designate, pan, zoom, inspect pixel and add decoy.
- [ ] Show detection box, track gate, predicted position, confidence ellipse, centroid,
  boresight and error vector with an uncluttered overlay legend.
- [ ] Add multi-target list with target ID, designated state, confidence and actions.
- [ ] Add loss/reacquisition overlay states and an operator-controlled dropout action.
- [ ] Add frame capture and short evidence-clip export with overlay metadata.
- [ ] Make all coordinate transforms correct under viewport scaling and resizing.

Exit gate: target designation, decoy rejection, loss and reacquisition can be performed
from the viewport and are obvious in both visuals and recorded telemetry.

## Phase 4 - Runtime Architecture and Control

Status: Not started

- [ ] Move frame generation and CV processing to a dedicated `QThread` worker.
- [ ] Keep all widgets on the Qt UI thread and use bounded latest-frame signals so a
  slow renderer cannot build an unbounded queue.
- [ ] Add Start, Pause, Stop, Step Frame and controlled Reset state transitions.
- [ ] Use monotonic timestamps, source timestamps for video and measured cycle timing.
- [ ] Add watchdog state for stalled video, processing overruns and worker exceptions.
- [ ] Implement deterministic seeded scenarios and record the seed in every report.
- [ ] Profile 640x480 and 2000x2000 source workflows; optimize only measured hotspots.

Exit gate: the UI remains responsive during worst-case noise and video processing,
shutdown is clean, and repeated seeded runs produce comparable results.

## Phase 5 - Evaluator Video Benchmark

Status: Core input path complete; reference scoring remains

- [x] Open MP4/AVI/MOV/MKV files and run at source FPS.
- [x] Bypass virtual target and PTZ frame generation for imported video.
- [x] Normalize source frames and process them through the production detector,
  Kalman state machine and telemetry recorder.
- [x] Control imported-video playback using the desktop Start/Pause/Reset workflow.
- [ ] Add seek, timeline, frame number, elapsed/remaining time and end-of-run summary.
- [ ] Load optional ground-truth centroid CSV using a documented schema.
- [ ] Preserve source-to-sensor scale transforms when comparing detected and reference
  centroids.
- [ ] Report centroid X/Y error, mean absolute error, RMSE, maximum error, precision,
  recall, acquisition/reacquisition and lock retention.
- [ ] Label pointing error and ground-truth centroid error separately everywhere.
- [ ] Export annotated video and a benchmark evidence bundle.

Exit gate: an evaluator can select a supplied 30 FPS MP4 and optional truth CSV, run it
without virtual PTZ, and receive reproducible metrics matching an independent checker.

## Phase 6 - Disturbance and Atmospheric Fidelity

Status: Functional baseline exists; physics upgrade remains

- [x] Implement selectable Gaussian, Poisson and salt-and-pepper sensor noise.
- [x] Implement camera jitter and selectable platform motion up to stated limits.
- [x] Implement clear, haze, fog, rain and low-light image conditions.
- [ ] Remove global random seeding and give each scenario an isolated reproducible RNG.
- [ ] Add measured disturbance previews and before/after image inspection.
- [ ] Implement von Karman/Kolmogorov spectral phase screens with configurable `Cn2`,
  inner scale, outer scale, aperture and wind advection.
- [ ] Keep simplified image-space atmosphere as a clearly labeled fast mode.
- [ ] Add cloud-occlusion schedules that produce traceable loss/recovery events.
- [ ] Validate distributions, bounds and spectral behavior with statistical tests.

Exit gate: every mandatory disturbance is selectable, bounded, reproducible and
measurably affects frames; physical-mode claims have equation-level validation.

## Phase 7 - Tracking, AI and Control Quality

Status: Strong baseline; systematic comparison remains

- [x] Provide intensity-weighted centroid, Gaussian fit and NCC modes.
- [x] Provide Kalman prediction, association gates, PID control and rate-limited gimbal.
- [x] Model independent pan and tilt limits and a fine-steering stage.
- [ ] Add detector confidence calibration and reject low-confidence false positives.
- [ ] Add connected-component diagnostics and robust subpixel Gaussian fitting.
- [ ] Implement dual-stage coarse-gimbal/FSM offload with measured bandwidth behavior.
- [ ] Add algorithm comparison runs over the same deterministic frame sequence.
- [ ] Add optional AI detector only if it improves a documented hard case; package the
  model locally and report model latency, version and confidence honestly.
- [ ] Add automated tuning and a field-safe PID tuning workflow with restore defaults.

Exit gate: algorithms are compared on fixed datasets and the selected default is
supported by measured accuracy, recovery, false-lock and latency results.

## Phase 8 - Orbital Mission Mode

Status: Not started

- [ ] Add optional SGP4 dependency and validated TLE input.
- [ ] Configure observer latitude, longitude, altitude and UTC mission time.
- [ ] Convert propagated state to topocentric azimuth/elevation with documented frames.
- [ ] Drive target truth and coarse pointing from the pass rather than a decorative
  two-dimensional curve.
- [ ] Show pass timeline, horizon entry/exit, max elevation and acquisition window.
- [ ] Bundle offline sample TLE missions; network fetching remains optional.

Exit gate: a known TLE/observer/time case matches an independent SGP4 reference within
documented tolerance and can drive a complete tracking run offline.

## Phase 9 - Evidence, Analysis and Reports

Status: Automatic baseline complete

- [x] Record automatic frame telemetry and JSON/text summaries per run.
- [x] Record duration, frame counts, average/max error, loss events, lock retention,
  processing time, acquisition and measured reacquisition.
- [ ] Add a Review workspace with run metadata, timeline, threshold table and event list.
- [ ] Use full-session aggregates for reports and rolling windows only for live display.
- [ ] Add percentile latency/error, jitter spectrum, false-lock count and per-state time.
- [ ] Add report identity: app version, commit, configuration, seed, source hash and UTC.
- [ ] Export a self-contained PDF report with plots and an evidence manifest.
- [ ] Add run comparison and baseline-regression views.

Exit gate: every value shown in Review can be traced to frame data, exported, reopened
and independently recomputed; unavailable evidence is shown as not evaluated.

## Phase 10 - Packaging, Documentation and Submission

Status: Not started

- [ ] Add pinned runtime and development dependency manifests.
- [ ] Make CI install dependencies before tests and benchmark execution.
- [ ] Build a versioned Windows executable with presets, icons and required Qt/OpenCV
  resources; verify on a clean Windows account.
- [ ] Add graceful crash logging and a user-facing recovery location.
- [ ] Replace the Vite starter README with real install, run, test and build instructions.
- [ ] Complete operator manual for simulation, video benchmark, configuration and reports.
- [ ] Produce the required 10-15 page technical report with measured benchmark results,
  architecture, algorithms, AI decisions, limitations and future hardware adapters.
- [ ] Create demonstration scenarios and a repeatable 10-15 minute evaluation script.
- [ ] Audit all software/documentation claims against the packaged binary.

Exit gate: the package runs offline on a clean evaluator machine, all mandatory
deliverables are present, and the evaluation script proves every stated requirement.

## Immediate Execution Order

1. Finish Phase 1 visual QA and persistent operator state.
2. Complete the Phase 2 mission editor and preflight flow.
3. Finish Phase 5 ground-truth video scoring because it carries 30% of evaluation.
4. Move processing to the Phase 4 worker thread before adding heavier physics.
5. Complete Phase 9 Review and evidence bundles.
6. Upgrade Phase 6 physics, Phase 7 control quality and Phase 8 orbital mode.
7. Close Phase 10 packaging and submission gates.

This order prioritizes the evaluator's first ten minutes, the two 30% benchmark stages,
and evidence integrity before optional technology breadth.
