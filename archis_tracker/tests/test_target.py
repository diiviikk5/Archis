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
