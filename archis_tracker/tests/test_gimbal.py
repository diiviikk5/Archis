"""Unit tests for Two-Axis Gimbal Pedestal dynamics."""
import pytest
from archis_tracker.core.gimbal import GimbalPedestal


def test_gimbal_rate_limiting():
    gimbal = GimbalPedestal(max_rate_deg_s=5.0)
    # Command excessive rate (15 deg/s)
    pan, tilt = gimbal.step(15.0, -12.0, dt=1.0)
    assert abs(gimbal.pan_vel_deg_s) <= 5.001, "Pan velocity must be clamped to max_rate"
    assert abs(gimbal.tilt_vel_deg_s) <= 5.001, "Tilt velocity must be clamped to max_rate"


def test_gimbal_gyro_readout():
    gimbal = GimbalPedestal(max_rate_deg_s=5.0)
    gimbal.step(3.0, 2.0, dt=0.5)
    pan_rate, tilt_rate = gimbal.read_gyro()
    assert abs(pan_rate - gimbal.pan_vel_deg_s) < 0.1, "Gyro rate should be close to true angular rate"
    assert abs(tilt_rate - gimbal.tilt_vel_deg_s) < 0.1
