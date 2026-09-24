# Archis FSOC Optical Tracker // Problem Statement SIH26169

[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)
[![OpenCV DNN](https://img.shields.io/badge/OpenCV-DNN%20Inference-green.svg)](https://opencv.org/)
[![PyQt6 Fluent](https://img.shields.io/badge/UI-PyQt6%20Fluent%20Design-purple.svg)](https://github.com/qfluentwidgets/PyQt-Fluent-Widgets)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An autonomous virtual camera tracking and pointing system for **Free-Space Optical Communications (FSOC)** beacon acquisition and tracking, designed around **Smart India Hackathon Problem Statement SIH26169**.

---

## 1. Specification Compliance Audit

The application includes a synthetic verification harness (`--benchmark`). The table
below records one current-model run on the development machine, not certification or
a flight-data evaluation. Re-run benchmarks on the target computer.

| ISRO Benchmark Parameter | Official Specification | Measured Performance (NanoSpot-Net AI) | Measured Performance (Gaussian Fit) | Compliance Status |
| :--- | :--- | :--- | :--- | :--- |
| **1. Acquisition Time** | <= 2.0 s | **0.33 s** | **0.33 s** | **PASSED [PASS]** |
| **2. Steady-State RMS Error** | <= 10.0 px | **0.65 px** | **0.75 px** | **PASSED [Synthetic]** |
| **3. Target Loss Rate** | < 5.0 % | **3.75 %** (under intentional obscuration) | **3.75 %** | **PASSED [PASS]** |
| **4. Re-acquisition Time** | <= 1.0 s | **0.30 s** | **0.30 s** | **PASSED [Sub-second]** |
| **5. Processing Throughput** | >= 20 FPS | **252.3 FPS** | **271.9 FPS** | **PASSED [Synthetic]** |

---

## 2. Core Architecture & Subsystems

`
+-----------------------------------------------------------------------------+
|                       ARCHIS FSOC OPTICAL TRACKER PIPELINE                  |
+-----------------------------------------------------------------------------+
                                      |
         +----------------------------+----------------------------+
         |                                                         |
         v                                                         v
+---------------------------------+       +---------------------------------+
|       VIRTUAL ENVIRONMENT       |       |    EXTERNAL VIDEO INGESTION     |
|  2000x2000 Continuous Canvas    |       |  Direct MP4 / AVI Camera Video  |
|  SDF Kinematics & Trajectories  |       |  Bypasses Synthetic Simulation  |
+---------------------------------+       +---------------------------------+
                 |                                         |
                 +--------------------+--------------------+
                                      |
                                      v
                      +-------------------------------+
                      |    FPA SENSOR & ATMOSPHERE    |
                      |  640x480 Monochrome Viewport  |
                      |  4 deg x 3 deg FOV            |
                      |  Kolmogorov Scintillation     |
                      |  Fog, Rain, Salt & Pepper     |
                      +-------------------------------+
                                      |
                                      v
                      +-------------------------------+
                      |   AI DEEP LEARNING DETECTOR   |
                      |  NanoSpot-Net (OpenCV DNN)    |
                      |  Learned Heatmap ONNX Graph  |
                      |  Sub-Pixel Power Moments      |
                      |  Spatial Eccentricity Decoy   |
                      +-------------------------------+
                                      |
                                      v
                      +-------------------------------+
                      |    KALMAN FILTER & TRACKING   |
                      |  Constant-Acceleration Kalman |
                      |  Mahalanobis Chi-Sq Gate      |
                      |  Dead-Reckoning Extrapolation |
                      +-------------------------------+
                                      |
                                      v
                      +-------------------------------+
                      |   PEDESTAL GIMBAL CONTROL     |
                      |  Anti-Windup Rate-Limited PID |
                      |  5 - 10 deg/s Slew Limits     |
                      |  Archimedean Re-acq Spiral    |
                      +-------------------------------+
`

### A. Experimental Learned Heatmap Detector
- A three-convolution CNN produces a 64x64 response heatmap through real OpenCV DNN inference.
- All convolution weights are trained on synthetic patches. Metadata includes the training seed, validation results and SHA-256 model identity.
- Subpixel refinement and eccentricity-based shape rejection are conventional post-processing, not learned coordinate or decoy heads.
- Response scores are uncalibrated. Synthetic tests do not establish flight-video accuracy.
- Missing, corrupt or failed models report an unavailable state; they never label classical detection as AI.
- Train with `python scripts/train_heatmap.py` (requires torch and onnx).
- Evaluate with `python scripts/evaluate_ai.py` (no training framework required).
- See [fresh-seed validation](docs/AI_VALIDATION.json) and [audit](docs/LIVE_UI_AI_AUDIT.md).

### B. Live Tracking Workspace
- Camera-first layout with compact transport controls and measured telemetry.
- Tabbed detector inspector and world view; the inspector can be hidden.
- Independent boresight, detection, prediction, error, search-gate and heatmap toggles.
- Heatmaps positioned over their actual inference crop, including acquisition.
- Resizable chart strip and lossless sensor-frame PNG capture.

---

## 3. Quick Start & Execution

### Option A: Standalone Executable (No Python Required)
Run the pre-compiled, self-contained single-file executable:
`powershell
# Launch interactive Windows 11 Fluent GUI
.\dist\ArchisOpticalTracker.exe

# Run automated headless benchmark audit
.\dist\ArchisOpticalTracker.exe --benchmark --duration 8.0 --algorithm ai
`

### Option B: From Python Source
`powershell
# Clone repository
git clone https://github.com/diiviikk5/Archis.git
cd Archis

# Install dependencies
pip install -r requirements.txt

# Launch GUI
python -m archis_tracker.main

# Run the full unit and desktop integration suite
python -m pytest archis_tracker/tests -v

# Run automated ISRO benchmark audit
python -m archis_tracker.main --benchmark --duration 8.0 --algorithm ai
`

---

## 4. Problem Statement Specifications Checklist

- [x] **Screen Canvas**: >= 2000 x 2000 px configurable canvas (EnvironmentConfig).
- [x] **Camera Sensor**: Monochrome Focal Plane Array (FPA), 640 x 480 resolution.
- [x] **Field of View (FOV)**: 4.0 deg x 3.0 deg default (109.08 urad/px IFOV).
- [x] **Frame Rate**: >= 30 Hz update clock (achieves > 270 FPS).
- [x] **Gimbal Slew Rate**: 5 - 10 deg/s software-enforced rate limiting with acceleration limits.
- [x] **Target Shapes**: Square (default), Circle, Gaussian Spot, Crosshair (5 - 20 px).
- [x] **Trajectories**: Straight Line, Circular, Figure of 8 (Lissajous), Random Walk, Spiral, Sinusoidal.
- [x] **Noise Injections**: Salt & Pepper (up to 10%), Gaussian (sigma <= 20), Poisson shot noise.
- [x] **Environmental Disturbances**: Mechanical jitter (+- 20 px), Platform motion, Fog, Rain, Haze, Scintillation.
- [x] **Centroiding Algorithms**: Intensity-Weighted Centroid, 2D Gaussian Surface Fit, Normalized Cross-Correlation, Deep Learning (NanoSpot-Net ONNX).
- [x] **External Video Ingestion**: Loading and tracking external MP4/AVI camera video files.
- [x] **Autonomous Re-acquisition**: Archimedean expanding spiral scan and Kalman dead-reckoning.
- [x] **Session Telemetry & Audit**: Real-time KPI dashboard, automated HTML/CSV/JSON session export.

---

