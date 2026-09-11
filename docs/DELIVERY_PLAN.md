# Archis Product Delivery

## Required End State

A standalone Windows application for virtual FSOC coarse pointing, with a complete
operator workflow and imported-video evaluation. Virtual environments are a required
input source, not a substitute for a working application. Hardware, real-time kernel,
GPU and communications-standard claims must describe implemented, verified behavior.

## Delivery Gates

- Configurable world (default 2000x2000), camera (640x480, 4x3 degrees, 30 Hz),
  target size/shape/location, multiple targets and designated-target tracking.
- Straight, circular, figure-eight and random motion; bounded pan/tilt control
  at least 20 Hz; automatic acquisition, loss handling and reacquisition.
- Selectable salt-and-pepper, Gaussian and Poisson noise; jitter, platform motion,
  clear/haze/fog/rain/low-light conditions, validated parameter limits.
- MP4 input at source timestamps, bypassing virtual PTZ, with optional reference
  centroids and honest centroid RMSE reporting when reference data exists.
- Start/pause/stop/reset, working presets, configuration save/load, onboarding,
  actionable errors, responsive desktop layout and persistent operator settings.
- Automatic per-run CSV and machine-readable/readable reports: duration, measured
  throughput, acquisition, average/maximum error, lock retention, processing time,
  loss events and reacquisition. Missing evidence must never appear as a pass.
- Reproducible scenario evaluation against acquisition <=2 s, tracking error <=10 px,
  loss <5%, reacquisition <=1 s and processing >=20 FPS. Distinguish centroid error
  from pointing error and session statistics from rolling display values.
- Connect the web interface to the actual engine if retained as an operational UI;
  remove unsupported aerospace stack and fabricated benchmark claims.
- Assess useful SGP4, spectral atmospheric and dual-stage control integrations;
  implement and validate applicable capabilities without claiming absent hardware.
- Installable/buildable standalone executable, dependency manifest, CI and verified
  packaged startup, resources, input processing and export.
- Complete documented source, operator manual and a 10-15 page technical report
  covering architecture, algorithms, AI use, tests, measured results and limitations.
- Commit and push incremental changes to the authorized origin repository.

## Initial Evidence

- Worktree clean at start; origin is https://github.com/diiviikk5/Archis.git.
- Existing Python suite: 17 passing tests.
- README is the unmodified Vite starter text; no dependency manifest was found.
- Desktop preset loader reads JSON but does not apply configuration.
- Telemetry passes acquisition without acquisition; benchmark mislabels failed
  reacquisition and excludes that requirement from its overall verdict.
- Existing engine generates virtual frames; imported-video evaluation is absent
  from the inspected entry point and tracking loop.

Completion requires current evidence for every gate above; this file is a work
ledger, not a declaration of readiness.
