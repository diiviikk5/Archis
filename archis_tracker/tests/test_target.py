"""Unit tests for TargetBeacon and trajectory generators."""
import pytest
import numpy as np
from archis_tracker.core.target import TargetBeacon
from archis_tracker.core.config import TargetConfig, TargetShape, MotionTrajectory


def test_target_shapes_and_sizes():
    for shape in TargetShape:
        for sz in [5, 10, 15, 20]:
            cfg = TargetConfig(shape=shape, size=sz)
            target = TargetBeacon(0, cfg)
            canvas = np.zeros((480, 640), dtype=np.float32)
            target.render_onto_viewport(canvas, 1000.0, 1000.0)
            assert np.max(canvas) > 0, f"Target {shape} with size {sz} should render on canvas"


def test_target_trajectories():
    for traj in MotionTrajectory:
        cfg = TargetConfig(trajectory=traj, speed=50.0)
        target = TargetBeacon(0, cfg)
        start_x, start_y = target.x, target.y
        
        # Step 60 frames
        dt = 1.0 / 30.0
        for _ in range(60):
            target.update(dt)
            
        dist = np.hypot(target.x - start_x, target.y - start_y)
        assert dist > 0.1, f"Trajectory {traj} should move target from starting position"


@pytest.mark.parametrize("trajectory", list(MotionTrajectory))
def test_motion_remains_continuous_across_speed_changes(trajectory):
    target = TargetBeacon(0, TargetConfig(trajectory=trajectory, speed=50.0))
    for frame in range(3600):
        if frame == 900:
            target.speed = 100.0
        previous = (target.x, target.y)
        target.update(1.0 / 30.0)
        assert np.hypot(target.x - previous[0], target.y - previous[1]) < 12.0


def test_straight_motion_bounces_and_responds_to_speed():
    target = TargetBeacon(0, TargetConfig(trajectory=MotionTrajectory.STRAIGHT_LINE, speed=60.0))
    target.reset_position(1949.0, 1000.0)
    target.update(1.0 / 30.0)
    target.update(1.0 / 30.0)
    assert target.vx < 0
    target.speed = 120.0
    target.update(1.0 / 30.0)
    assert np.hypot(target.vx, target.vy) == pytest.approx(120.0)


def test_zero_time_step_does_not_move_target():
    target = TargetBeacon(0)
    target.update(0)
    assert (target.x, target.y, target.time_elapsed) == (1000.0, 1000.0, 0.0)
