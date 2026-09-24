"""Tests for the explicit two-terminal 3D simulation geometry."""
from __future__ import annotations

from copy import deepcopy
import math

import pytest

from archis_tracker.core.camera import VirtualCamera
from archis_tracker.core.config import (
    CameraConfig,
    EnvironmentConfig,
    TargetConfig,
    TerminalWorldConfig,
)
from archis_tracker.core.target import TargetBeacon, TargetManager
from archis_tracker.core.scenario import (
    DEFAULT_SCENARIO,
    Scenario,
    ScenarioError,
    tracker_from_scenario,
    validate_scenario,
)
from archis_tracker.core.tracker import TrackingSystem
from archis_tracker.core.world_model import TerminalRole, TwoTerminalWorldModel


def _scene(range_m: float = 1000.0):
    camera_config = CameraConfig()
    environment_config = EnvironmentConfig()
    camera = VirtualCamera(camera_config, environment_config)
    target = TargetBeacon(1, TargetConfig(initial_x=1000.0, initial_y=1000.0, range_m=range_m))
    model = TwoTerminalWorldModel(camera_config, environment_config)
    return camera, target, model


def test_centered_terminals_have_explicit_3d_pose_range_and_orientation():
    camera, target, model = _scene(1250.0)
    snapshot = model.reset(camera, target)

    assert snapshot.receiver.role == TerminalRole.RECEIVER
    assert snapshot.transmitter.role == TerminalRole.TRANSMITTER
    assert snapshot.receiver.position_m.x == 0.0
    assert snapshot.transmitter.position_m.z == pytest.approx(1250.0)
    assert snapshot.separation_m == pytest.approx(1250.0)
    assert snapshot.line_of_sight_azimuth_deg == pytest.approx(0.0)
    assert snapshot.line_of_sight_elevation_deg == pytest.approx(0.0)
    assert abs(snapshot.transmitter.orientation.yaw_deg) == pytest.approx(180.0)
    assert snapshot.transmitter_in_fov


def test_gimbal_boresight_and_fov_use_relative_3d_angles():
    camera, target, model = _scene()
    target.x += camera.config.pixels_per_deg_x
    target.y -= camera.config.pixels_per_deg_y

    off_axis = model.reset(camera, target)
    assert off_axis.line_of_sight_azimuth_deg == pytest.approx(1.0)
    assert off_axis.line_of_sight_elevation_deg == pytest.approx(1.0)
    assert off_axis.relative_azimuth_deg == pytest.approx(1.0)
    assert off_axis.relative_elevation_deg == pytest.approx(1.0)
    assert off_axis.transmitter_in_fov

    camera.pan_deg = 1.0
    camera.tilt_deg = -1.0
    camera.gimbal.pan_angle_deg = 1.0
    camera.gimbal.tilt_angle_deg = -1.0
    camera.update_world_position()
    aligned = model.update(0.0, camera, target)
    assert aligned.camera.boresight_azimuth_deg == pytest.approx(1.0)
    assert aligned.camera.boresight_elevation_deg == pytest.approx(1.0)
    assert aligned.relative_azimuth_deg == pytest.approx(0.0)
    assert aligned.relative_elevation_deg == pytest.approx(0.0)


def test_receiver_and_transmitter_publish_physical_velocity():
    camera_config = CameraConfig()
    environment_config = EnvironmentConfig()
    config = TerminalWorldConfig(receiver_velocity_m_s=(5.0, -2.0, 1.0))
    camera = VirtualCamera(camera_config, environment_config)
    target = TargetBeacon(1, TargetConfig(initial_x=1000.0, initial_y=1000.0))
    model = TwoTerminalWorldModel(camera_config, environment_config, config)
    model.reset(camera, target)

    snapshot = model.update(2.0, camera, target)
    assert snapshot.receiver.position_m.x == pytest.approx(10.0)
    assert snapshot.receiver.position_m.y == pytest.approx(-4.0)
    assert snapshot.receiver.position_m.z == pytest.approx(2.0)
    assert snapshot.receiver.velocity_m_s.x == pytest.approx(5.0)
    assert snapshot.transmitter.velocity_m_s.x == pytest.approx(5.0)
    assert snapshot.transmitter.velocity_m_s.y == pytest.approx(-2.0)
    assert snapshot.transmitter.velocity_m_s.z == pytest.approx(1.0)


def test_multiple_decoys_become_distinct_3d_terminal_states():
    camera, target, model = _scene()
    manager = TargetManager(target.config)
    manager.primary_target = target
    manager.add_decoy(1160.0, 1000.0, range_m=2000.0)
    manager.add_decoy(1000.0, 840.0, range_m=3000.0)

    snapshot = model.reset(camera, manager.primary_target, manager.secondary_targets)
    assert [terminal.role for terminal in snapshot.decoys] == [TerminalRole.DECOY, TerminalRole.DECOY]
    assert [terminal.terminal_id for terminal in snapshot.decoys] == ["TX-2", "TX-3"]
    ranges = [
        (terminal.position_m - snapshot.receiver.position_m).magnitude
        for terminal in snapshot.decoys
    ]
    assert ranges == pytest.approx([2000.0, 3000.0])


def test_tracking_system_keeps_world_snapshot_out_of_detector_inputs():
    tracker = TrackingSystem(
        target_config=TargetConfig(initial_x=1080.0, initial_y=920.0, range_m=2500.0)
    )
    tracker.spawn_decoy(920.0, 1080.0, range_m=1800.0)
    tracker.step(1 / 30)

    assert tracker.world_snapshot.separation_m == pytest.approx(2500.0)
    assert len(tracker.world_snapshot.decoys) == 1
    assert tracker.last_result is not None
    assert tracker.last_result.diagnostics["terminal_range_m"] == pytest.approx(2500.0)
    assert "terminal_range_m" not in tracker.last_result.frame.metadata
    assert math.isfinite(tracker.world_snapshot.transmitter.velocity_m_s.magnitude)


def test_scenario_configures_and_validates_physical_terminal_geometry():
    raw = deepcopy(DEFAULT_SCENARIO)
    raw["world"]["nominal_range_m"] = 4200.0
    raw["world"]["receiver_position_m"] = [10.0, 20.0, 30.0]
    raw["world"]["receiver_velocity_m_s"] = [1.0, 2.0, 3.0]
    raw["target"]["range_m"] = 3500.0
    raw["target"]["orientation_deg"] = [175.0, -2.0, 1.0]

    tracker = tracker_from_scenario(Scenario(validate_scenario(raw)))
    snapshot = tracker.world_snapshot
    assert snapshot.receiver.position_m.x == pytest.approx(10.0)
    assert snapshot.receiver.velocity_m_s.z == pytest.approx(3.0)
    assert snapshot.separation_m == pytest.approx(3500.0)
    assert snapshot.transmitter.orientation.yaw_deg == pytest.approx(175.0)

    invalid = deepcopy(raw)
    invalid["world"]["receiver_position_m"] = [0.0, 0.0]
    with pytest.raises(ScenarioError, match="must contain three numbers"):
        validate_scenario(invalid)
