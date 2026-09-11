"""Imported frames use the production detector and telemetry path."""
import cv2
import numpy as np

from archis_tracker.core.tracker import TrackingSystem


def test_external_frame_bypasses_simulation_and_tracks_beacon():
    tracker = TrackingSystem()
    frame = np.zeros((720, 960, 3), dtype=np.uint8)
    cv2.circle(frame, (480, 360), 9, (255, 255, 255), -1)

    detection = tracker.step_external_frame(frame, 1 / 30)

    assert detection.detected
    assert abs(detection.x - 320) < 2
    assert abs(detection.y - 240) < 2
    assert tracker.telemetry.total_frames == 1
    assert tracker.camera.pan_deg == 0
    assert tracker.camera.tilt_deg == 0
