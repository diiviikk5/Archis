"""
Archis Optical Tracker - Core Module
"""
from .config import (CameraConfig, EnvironmentConfig, TargetConfig, 
                     DisturbanceConfig, ControllerConfig, PerformanceThresholds,
                     TargetShape, MotionTrajectory, AtmosphericCondition, 
                     PlatformMotionType, TrackingState)
from .environment import VirtualEnvironment
from .target import TargetBeacon
from .camera import VirtualCamera
from .disturbances import DisturbanceEngine
from .detector import BeaconDetector, DetectionResult
from .kalman_filter import KalmanFilter2D
from .controller import GimbalController
from .telemetry import TelemetryEngine
from .tracker import TrackingSystem
from .contracts import (
    CameraCommand, CanonicalTrackingState, Detection, FramePacket,
    GroundTruthSample, TrackEstimate, TrackingResult,
)
from .performance import PerformanceRecorder, PerformanceSummary
from .optics import PinholeCameraModel
from .scenario import Scenario, ScenarioError, load_scenario, tracker_from_scenario

__all__ = [
    "CameraConfig", "EnvironmentConfig", "TargetConfig", "DisturbanceConfig",
    "ControllerConfig", "PerformanceThresholds", "TargetShape", "MotionTrajectory",
    "AtmosphericCondition", "PlatformMotionType", "TrackingState",
    "VirtualEnvironment", "TargetBeacon", "VirtualCamera", "DisturbanceEngine",
    "BeaconDetector", "DetectionResult", "KalmanFilter2D", "GimbalController",
    "TelemetryEngine", "TrackingSystem", "CameraCommand",
    "CanonicalTrackingState", "Detection", "FramePacket", "GroundTruthSample",
    "TrackEstimate", "TrackingResult", "PinholeCameraModel",
    "PerformanceRecorder", "PerformanceSummary",
    "Scenario", "ScenarioError", "load_scenario", "tracker_from_scenario",
]
