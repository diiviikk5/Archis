"""Imported frames use the production detector and telemetry path."""
import cv2
import numpy as np

from archis_tracker.core.sources import ImageSequenceSource
from archis_tracker.core.tracker import TrackingSystem


def test_external_frame_bypasses_simulation_and_tracks_beacon():
    tracker = TrackingSystem()
    frame = np.zeros((720, 960, 3), dtype=np.uint8)
    cv2.circle(frame, (480, 360), 9, (255, 255, 255), -1)

    detection = tracker.step_external_frame(frame, 1 / 30)

    assert detection.detected
    # Evaluator recordings are processed at native resolution; coordinates
    # therefore remain in the input sensor frame instead of being resized.
    assert abs(detection.x - 480) < 2
    assert abs(detection.y - 360) < 2
    assert tracker.current_frame.shape == (720, 960)
    assert tracker.telemetry.total_frames == 1
    assert tracker.camera.pan_deg == 0
    assert tracker.camera.tilt_deg == 0


def test_bgra_still_frames_and_natural_sequence_order(tmp_path):
    for name, value in (("frame10.png", 10), ("frame2.png", 2), ("frame1.png", 1)):
        image = np.zeros((48, 64, 4), dtype=np.uint8)
        image[:, :, 3] = 255
        image[20:28, 28:36, :3] = value * 20
        assert cv2.imwrite(str(tmp_path / name), image)
    source = ImageSequenceSource(tmp_path)
    assert [source.read().metadata["path"].split("/")[-1] for _ in range(3)] == [
        "frame1.png", "frame2.png", "frame10.png"
    ]
    tracker = TrackingSystem()
    bgra = cv2.imread(str(tmp_path / "frame10.png"), cv2.IMREAD_UNCHANGED)
    tracker.step_external_frame(bgra, 1/30)
    assert tracker.current_frame.shape == (48, 64)
