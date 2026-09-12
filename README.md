# Archis FSOC Optical Tracker // Problem Statement SIH26169

[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)
[![OpenCV DNN](https://img.shields.io/badge/OpenCV-DNN%20Inference-green.svg)](https://opencv.org/)
[![PyQt6 Fluent](https://img.shields.io/badge/UI-PyQt6%20Fluent%20Design-purple.svg)](https://github.com/qfluentwidgets/PyQt-Fluent-Widgets)
[![ISRO Compliance](https://img.shields.io/badge/ISRO%20Audit-5%2F5%20PASSED-emerald.svg)](#1-specification-compliance-audit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An instrument-grade, autonomous virtual camera tracking and pointing system engineered for **Free-Space Optical Communications (FSOC)** optical beacon acquisition and tracking, adhering strictly to **ISRO specifications (Smart India Hackathon Problem Statement SIH26169)**.

---

## 1. Specification Compliance Audit

The application includes an automated verification harness (--benchmark) that directly evaluates the closed-loop tracking pipeline against all 5 official ISRO performance criteria.

| ISRO Benchmark Parameter | Official Specification | Measured Performance (NanoSpot-Net AI) | Measured Performance (Gaussian Fit) | Compliance Status |
| :--- | :--- | :--- | :--- | :--- |
| **1. Acquisition Time** | <= 2.0 s | **0.33 s** | **0.33 s** | **PASSED [PASS]** |
| **2. Steady-State RMS Error** | <= 10.0 px | **0.94 px** | **0.75 px** | **PASSED [Sub-pixel]** |
| **3. Target Loss Rate** | < 5.0 % | **3.75 %** (under intentional obscuration) | **3.75 %** | **PASSED [PASS]** |
| **4. Re-acquisition Time** | <= 1.0 s | **0.30 s** | **0.30 s** | **PASSED [Sub-second]** |
| **5. Processing Throughput** | >= 20 FPS | **271.0 FPS** (3.69 ms/frame) | **271.9 FPS** | **PASSED [13x Margin]** |

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
                      |  10.5 KB Dual-Head ONNX Graph |
                      |  Sub-Pixel Power Moments      |
                      |  Spatial Eccentricity Decoy   |
                      +-------------------------------+
                                      |
                                      v
                      +-------------------------------+
                      |    KALMAN FILTER & TRACKING   |
                      |  Extended Kalman State Est.   |
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

### A. Deep Learning Optical Spot Detector (NanoSpot-Net)
- **Dual-Head Neural Network**:
  - Head 1: 64x64 spatial probability heatmap surface.
  - Head 2: Coordinate regression vector [x_sub, y_sub, sigma_x, sigma_y].
- **OpenCV DNN CPU Inference**: Runs via cv2.dnn.readNetFromONNX in **0.35 ms (~2,880 FPS)** on CPU. Zero heavy framework dependencies like PyTorch in runtime.
- **Continuous Sub-Pixel Centroiding**: Power-weighted 2nd order local moments achieve continuous accuracy < 0.05 px.
- **Decoy Flare Discrimination**: Computes spatial inertia tensor eigenvalues on optical patches. Elongated flares (e = 0.91) are rejected above the e > 0.70 threshold, while circular laser spots (e = 0.0004) pass.

### B. Windows 11 Fluent Design System UI
- **NavigationInterface**: Expandable sidebar with smooth transitions, embedded station logo avatar, and zero text truncation.
- **Tactical Cockpit HUD Viewport**:
  - Live 64x64 cyan/emerald glowing neural probability heatmap overlay inside track gate.
  - Reticle color adaptation (LOCKED TRACKING emerald, DEAD RECKONING amber, SEARCHING cyan, LOST rose).
  - Floating WARNING: DECOY FLARE REJECTED banner.
  - Interactive Click-to-Designate (Left Click) and Spawn Decoy (Right Click).
- **Telemetry KPI Bar**: Real-time compliance badges with pass/fail threshold indicators.
- **Comprehensive Setup Console**: Target profile, Optics & CV selector, Gimbal pedestal rate limits, and Disturbance injectors.

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

# Run full pytest suite (30/30 unit tests)
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

