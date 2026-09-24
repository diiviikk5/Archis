# Archis Optical Tracker 2.0

Archis is an AI-assisted virtual camera tracking laboratory for Smart India Hackathon problem statement 26169: coarse alignment of mobile free-space optical communication terminals.

It combines a polished PyQt/Fluent simulator with a deterministic tracking and evaluation engine. The default hybrid pipeline performs full-frame robust acquisition, NanoSpot refinement, compact candidate verification, temporal confirmation, optional CodeLock identity checks, Kalman tracking, and bounded pan/tilt control.

## What is included

- Configurable 2000×2000 virtual world, beacon shapes and trajectories.
- Fixed-step, seeded noise, atmosphere, platform motion, jitter, scheduled dropout, and deterministic burst loss.
- Explicit `SEARCH → ACQUIRE → TRACK → COAST → REACQUIRE` state machine.
- Six-state acceleration-aware Kalman estimation with confidence-scaled measurement noise, Joseph covariance correction, and catastrophic-jump rejection.
- Optional latency-compensated aimpoints using estimated position, velocity, and acceleration.
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

Simulation applies effects in this order: world and targets, camera pose, platform motion/jitter, atmosphere/blur, sensor noise, then dropout. Scheduled dropout can be combined with a deterministic two-state burst-loss process. Sensor-space truth is calculated after geometry and sent only to visualization and evaluation.

The estimator uses a strict candidate-association gate followed by a deliberately wider Kalman sanity gate. Periodic full-frame safety scans therefore remain capable of finding the target without allowing an unrelated bright candidate to cause a catastrophic state jump. The correction uses the Joseph covariance form to retain covariance symmetry and positive semi-definiteness under finite precision.

### New scenario controls

Schema-v2 scenarios can enable the AstraTrack-inspired features without changing existing preset behavior:

```json
{
  "disturbances": {
    "dropout": {
      "enabled": false,
      "start_s": 20.0,
      "duration_s": 0.3,
      "burst_enabled": true,
      "mean_clear_s": 8.0,
      "mean_loss_s": 0.25
    }
  },
  "detector": {
    "innovation_gate_chi2": 10000.0
  },
  "controller": {
    "latency_compensation_s": 0.075
  }
}
```

`mean_clear_s` and `mean_loss_s` are mean dwell times for a continuous-time two-state loss process. Transition probabilities are derived from the sensor timestep, and the channel has an isolated RNG stream, so identical seeds reproduce identical loss sequences without perturbing the other noise channels. `latency_compensation_s` should represent known sensor, processing, transport, and actuator delay; leave it at `0.0` when no delay is being modelled.

## AstraTrack selective-upgrade comparison

AstraTrack commit `856b483f89f33a77b61c8735f48df6a79a75c994` was reviewed module-by-module. Concepts were reimplemented only where they strengthened Archis; its UI, HSV detector, model-less “AI” fallback, heuristic uncertainty expansion, periodic pseudo-random blackout, and process-randomized `hash()` seeding were not imported.

| Area | Before | Current Archis | Result |
| --- | --- | --- | --- |
| Kalman correction | Abbreviated covariance update | Joseph-form covariance update with symmetry restoration | Better long-run numerical stability |
| Estimator outliers | Candidate association gate only | Candidate gate plus configurable catastrophic-jump sanity gate | Defense in depth against false state jumps |
| Periodic safety scan | Full-frame scan could bypass the local prediction gate | Full-frame search retained while confirmed estimates remain sanity-gated | Safer decoy handling |
| Motion compensation | PID plus velocity feed-forward | Optional position/velocity/acceleration lead projection for known latency | Supports delayed video and actuator pipelines |
| Dropout testing | One scheduled blackout window | Scheduled window plus seeded two-state burst loss | More realistic repeatable fade/loss stress tests |
| Randomness isolation | Shared disturbance RNG | Separate stable burst-loss RNG stream | Enabling dropout does not change unrelated noise |
| Configuration | Scheduled dropout fields only | Validated schema and legacy-preset fields for burst loss, estimator gate, and latency | Reproducible CLI/UI-compatible configuration |
| Benchmark serialization | NumPy booleans could fail JSON serialization when a target left the FOV | Visibility normalized to a native boolean | Reliable long-run evidence export |
| UI timing test | Assumed synchronous processing | Waits for the existing worker-thread completion signal | Tests the non-blocking UI architecture correctly |

### Before/after benchmark

Both columns below use `scenarios/schema_v2_example.json`, 1,800 frames at 30 Hz, seed `26169`, and the same development machine. “Before” is engine commit `2f2e0f6`; “after” is engine commit `93e432a`. Accuracy and state metrics are deterministic for the recorded seed. Processing throughput is wall-clock dependent and should not be treated as an algorithmic accuracy metric.

| Metric | Before | After | Change | SIH gate |
| --- | ---: | ---: | ---: | --- |
| Acquisition time | 0.333 s | 0.333 s | No change | ≤ 2 s — Pass |
| Centroid RMSE | 2.455 px | 2.486 px | +0.030 px | ≤ 10 px — Pass |
| Pointing RMSE | 3.370 px | 3.343 px | **−0.028 px** | ≤ 10 px — Pass |
| Lock retention | 98.827% | 98.827% | No change | Loss < 5% — Pass |
| Target loss | 1.173% | 1.173% | No change | < 5% — Pass |
| Reacquisition events | 3 | 2 | **1 fewer** | Informational |
| Worst reacquisition | 0.300 s | 0.333 s | +0.033 s | ≤ 1 s — Pass |
| Processing throughput | 37.29 FPS | 36.30 FPS | −0.99 FPS | ≥ 20 FPS — Pass |
| Overall strict result | Pass | Pass | All release gates retained | Pass |

The small centroid/reacquisition differences come from the numerically stable covariance correction changing finite-precision filter evolution. The default profile retains the same lock and loss rates, slightly improves pointing RMSE, and remains comfortably inside every release gate. Latency compensation and burst loss are opt-in, so existing presets keep their established behavior.

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

The unified suite currently contains **84 passing tests**. The count includes every parameterized case and covers acquisition at the frame center/edges/corners, truth isolation, repeatability, state transitions, CodeLock, controller bounds, preset migration, native-resolution media, truth sidecars, metrics, headless UI startup, estimator outlier rejection, latency compensation, deterministic burst loss, and report export.

| Test module | Passing cases | Coverage |
| --- | ---: | --- |
| `test_ai_detector.py` | 14 | Real NanoSpot inference, failures, provenance, heatmaps, decoys |
| `test_association.py` | 2 | Mahalanobis association and decoy rejection |
| `test_camera.py` | 3 | Camera geometry, rate limits, coordinate transforms |
| `test_controller.py` | 2 | PID direction and autonomous search spiral |
| `test_detector.py` | 2 | Clean and noisy optical-beacon detection |
| `test_disturbances.py` | 7 | Noise, atmosphere, jitter, turbulence, repeatable burst loss |
| `test_external_video.py` | 2 | Native external frames, BGRA images, sequence ordering |
| `test_gimbal.py` | 2 | Gimbal dynamics and gyro telemetry |
| `test_optics.py` | 3 | FOV intrinsics and angular geometry |
| `test_performance_v2.py` | 5 | Truth-based reports, honest truth-free metrics, fingerprints |
| `test_playback_ui.py` | 5 | Worker pacing, native viewport size, overlays, capture, controls |
| `test_presets.py` | 3 | Live preset application, atomic rejection, independent limits |
| `test_session_report.py` | 1 | Automatic CSV/JSON/HTML session evidence |
| `test_target.py` | 10 | Shapes, six trajectories, continuity, bounce, zero timestep |
| `test_telemetry.py` | 4 | Empty runs, loss limits, reacquisition, aggregate telemetry |
| `test_unified_core.py` | 19 | Contracts, state machine, seeds, truth, CodeLock, new estimator features |
| **Total** | **84** | **All passing** |

<details>
<summary>Complete passing test inventory</summary>

#### AI detector — 14

- `test_ai_detector_initialization`
- `test_ai_detector_beacon_spot`
- `test_ai_detector_decoy_rejection`
- `test_ai_detector_pure_noise`
- `test_beacon_detector_ai_integration`
- `test_missing_model_does_not_masquerade_as_ai`
- `test_corrupt_model_is_reported`
- `test_real_inference_tracks_input_not_fixed_coordinates[xy0]`
- `test_real_inference_tracks_input_not_fixed_coordinates[xy1]`
- `test_real_inference_tracks_input_not_fixed_coordinates[xy2]`
- `test_model_provenance_matches_bundled_weights`
- `test_threshold_and_shape_filter_affect_real_inference`
- `test_inference_failure_is_explicit`
- `test_ai_gate_heatmap_uses_sensor_coordinates`

#### Association, camera, controller, and detector — 9

- `test_mahalanobis_gating_selects_closest_statistical_candidate`
- `test_decoy_rejection_outside_gate`
- `test_camera_dimensions_and_fov`
- `test_camera_pan_tilt_rate_limiting`
- `test_coordinate_transforms`
- `test_pid_error_convergence`
- `test_search_spiral`
- `test_beacon_detection_clean`
- `test_detection_under_gaussian_noise`

#### Disturbances — 7

- `test_image_noise_injections`
- `test_camera_jitter_and_platform_bounds`
- `test_atmospheric_conditions`
- `test_turbulence_and_scintillation_are_seeded_and_repeatable`
- `test_turbulence_controls_are_independent`
- `test_burst_dropout_is_seeded_repeatable_and_resettable`
- `test_scheduled_and_burst_dropout_share_one_status_api`

#### External sources, gimbal, and optics — 7

- `test_external_frame_bypasses_simulation_and_tracks_beacon`
- `test_bgra_still_frames_and_natural_sequence_order`
- `test_gimbal_rate_limiting`
- `test_gimbal_gyro_readout`
- `test_pinhole_intrinsics_match_configured_field_of_view`
- `test_sensor_edge_is_half_fov_from_boresight`
- `test_angular_separation_is_symmetric_and_validates_geometry`

#### Performance and reports — 6

- `test_performance_report_uses_truth_and_exports_three_formats`
- `test_truth_free_recording_does_not_claim_accuracy`
- `test_invisible_truth_is_logged_but_not_claimed_as_accuracy`
- `test_expected_dropout_requires_a_measured_reacquisition`
- `test_identical_seed_runs_have_identical_report_fingerprint`
- `test_session_writes_csv_json_and_readable_report`

#### Desktop playback — 5

- `test_playback_preserves_sensor_period`
- `test_viewport_uses_actual_frame_dimensions`
- `test_overlay_controls_do_not_change_sensor_frame`
- `test_capture_writes_real_frame`
- `test_turbulence_controls_update_live_configuration`

#### Presets — 3

- `test_bundled_preset_applies_to_live_subsystems`
- `test_invalid_preset_is_rejected_before_mutation`
- `test_pan_and_tilt_limits_are_applied_independently`

#### Targets — 10

- `test_target_shapes_and_sizes`
- `test_target_trajectories`
- `test_motion_remains_continuous_across_speed_changes[MotionTrajectory.STRAIGHT_LINE]`
- `test_motion_remains_continuous_across_speed_changes[MotionTrajectory.CIRCULAR]`
- `test_motion_remains_continuous_across_speed_changes[MotionTrajectory.FIGURE_OF_8]`
- `test_motion_remains_continuous_across_speed_changes[MotionTrajectory.RANDOM]`
- `test_motion_remains_continuous_across_speed_changes[MotionTrajectory.SPIRAL]`
- `test_motion_remains_continuous_across_speed_changes[MotionTrajectory.SINUSOIDAL]`
- `test_straight_motion_bounces_and_responds_to_speed`
- `test_zero_time_step_does_not_move_target`

#### Telemetry — 4

- `test_empty_session_cannot_pass_benchmark`
- `test_unresolved_loss_and_exact_loss_limit_fail`
- `test_completed_reacquisition_is_measured`
- `test_telemetry_metrics_tracking`

#### Unified core — 19

- `test_initial_acquisition_is_full_frame[xy0]`
- `test_initial_acquisition_is_full_frame[xy1]`
- `test_initial_acquisition_is_full_frame[xy2]`
- `test_initial_acquisition_is_full_frame[xy3]`
- `test_contracts_are_immutable_and_truth_is_separate`
- `test_explicit_state_machine_coasts_and_reacquires`
- `test_seeded_simulation_is_reproducible`
- `test_configured_seed_rebuilds_all_random_sources`
- `test_truth_sidecars_support_csv_json_and_opt_in_interpolation`
- `test_legacy_preset_migrates_to_schema_v2`
- `test_scenario_validation_rejects_bad_seed`
- `test_codelock_rejects_constant_light_and_accepts_pattern`
- `test_native_external_truth_populates_centroid_metrics`
- `test_native_external_theoretical_command_uses_native_sensor_center`
- `test_schema_v2_can_create_primary_and_decoy_targets`
- `test_codelock_rejects_invalid_runtime_configuration`
- `test_kalman_rejects_statistical_outlier_and_preserves_covariance_health`
- `test_kinematic_prediction_and_latency_compensated_aimpoint`
- `test_scenario_builds_burst_loss_and_latency_compensation`

</details>

## Windows release

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1
```

The script runs tests, creates the one-folder application, packages a portable ZIP, builds the installer when Inno Setup is available, and writes SHA-256 checksums and a release manifest. Keep every file in `dist\ArchisTracker` together. The executable is `dist\ArchisTracker\ArchisTracker.exe`.

## Provenance

Archis1 commit `06022f1` is the product baseline. Qlyraxis commit `2514c5d` supplied the deterministic tracking-core reference. AstraTrack commit `856b483f89f33a77b61c8735f48df6a79a75c994` supplied selected estimator, latency, and disturbance-testing ideas that were independently validated and reimplemented. Unrelated Git histories were not merged. Existing Archis preset names and the Fluent desktop workflow remain authoritative.

The formal technical report and user manual are intentionally deferred to the final submission pass.
