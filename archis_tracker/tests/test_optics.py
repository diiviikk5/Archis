from __future__ import annotations

import math

import pytest

from archis_tracker.core.optics import PinholeCameraModel


def test_pinhole_intrinsics_match_configured_field_of_view():
    model = PinholeCameraModel(640, 480, 4.0, 3.0)
    assert model.fx_px == pytest.approx(640 / (2 * math.tan(math.radians(2.0))))
    assert model.fy_px == pytest.approx(480 / (2 * math.tan(math.radians(1.5))))
    assert model.boresight_offset_urad(320, 240) == pytest.approx(0.0)


def test_sensor_edge_is_half_fov_from_boresight():
    model = PinholeCameraModel(640, 480, 4.0, 3.0)
    assert model.boresight_offset_urad(640, 240) == pytest.approx(math.radians(2.0) * 1e6)
    assert model.boresight_offset_urad(320, 0) == pytest.approx(math.radians(1.5) * 1e6)


def test_angular_separation_is_symmetric_and_validates_geometry():
    model = PinholeCameraModel(640, 480, 4.0, 3.0)
    forward = model.angular_separation_urad((100, 120), (400, 300))
    reverse = model.angular_separation_urad((400, 300), (100, 120))
    assert forward == pytest.approx(reverse)
    with pytest.raises(ValueError):
        PinholeCameraModel(640, 480, 180.0, 3.0)
