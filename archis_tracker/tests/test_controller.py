"""Unit tests for PID tracking controller and search spiral."""
import pytest
import numpy as np
from archis_tracker.core.controller import GimbalController
from archis_tracker.core.config import ControllerConfig, CameraConfig


def test_pid_error_convergence():
    ctrl = GimbalController()
    # If target is at (352, 240) (error = +32px on X)
    cmd_pan, cmd_tilt = ctrl.compute_tracking_command(352.0, 240.0, 0.0, 0.0, 1.0 / 30.0)
    assert cmd_pan > 0.0, "+X error must command +Pan velocity to center target"
    assert abs(cmd_tilt) < 0.1, "Zero Y error should yield near zero Tilt velocity"


def test_search_spiral():
    ctrl = GimbalController()
    ctrl.start_search(0.0, 0.0)
    
    # Step spiral for 1.0s
    dt = 1.0 / 30.0
    for _ in range(30):
        pan_vel, tilt_vel = ctrl.compute_search_command(dt)
        assert np.hypot(pan_vel, tilt_vel) > 0.1, "Search command must produce active scan velocity"
