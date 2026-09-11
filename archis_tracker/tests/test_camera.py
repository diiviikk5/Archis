"""Unit tests for VirtualCamera pan/tilt kinematics and rate limits."""
import pytest
import numpy as np
from archis_tracker.core.camera import VirtualCamera
from archis_tracker.core.config import CameraConfig


def test_camera_dimensions_and_fov():
    cam = VirtualCamera()
    assert cam.width == 640
    assert cam.height == 480
    assert cam.config.fov_x_deg == 4.0
    assert cam.config.fov_y_deg == 3.0
    assert cam.config.pixels_per_deg_x == 160.0
    assert cam.config.pixels_per_deg_y == 160.0


def test_camera_pan_tilt_rate_limiting():
    cam = VirtualCamera()
    cam.max_pan_speed_deg_s = 5.0  # Specification: 5-10 °/s
    cam.max_tilt_speed_deg_s = 5.0
    
    dt = 1.0  # 1 second
    # Command 20 °/s (exceeding limit)
    cam.apply_pan_tilt_command(20.0, -20.0, dt)
    
    # Must be clamped strictly to 5.0 °/s
    assert abs(cam.pan_velocity_deg_s) <= 5.0
    assert abs(cam.tilt_velocity_deg_s) <= 5.0
    assert abs(cam.pan_deg) <= 5.0
    assert abs(cam.tilt_deg) <= 5.0


def test_coordinate_transforms():
    cam = VirtualCamera()
    # At origin (1000, 1000), center in viewport is (320, 240)
    vx, vy = cam.world_to_viewport(1000.0, 1000.0)
    assert abs(vx - 320.0) < 1e-4
    assert abs(vy - 240.0) < 1e-4
    
    # Invert
    wx, wy = cam.viewport_to_world(320.0, 240.0)
    assert abs(wx - 1000.0) < 1e-4
    assert abs(wy - 1000.0) < 1e-4
