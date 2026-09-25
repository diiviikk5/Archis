"""Mission presets must configure the live engine, not only the UI."""
import json

import pytest

from archis_tracker.core.config import AtmosphericCondition, MotionTrajectory
from archis_tracker.core.presets import PresetError
from archis_tracker.core.scenario import load_scenario, tracker_from_scenario
from archis_tracker.core.tracker import TrackingSystem


def test_bundled_preset_applies_to_live_subsystems():
    tracker = TrackingSystem()
    preset = tracker.load_preset("archis_tracker/presets/heavy_turbulence.json")

    assert preset.name == "Heavy Atmospheric Turbulence"
    assert tracker.primary_target.trajectory == MotionTrajectory.CIRCULAR
    assert tracker.primary_target.size == 14
    assert tracker.disturbances.config.atmospheric_condition == AtmosphericCondition.FOG
    assert tracker.disturbances.config.enable_gaussian_noise
    assert tracker.disturbances.config.turbulence_warp_px == 3.5
    assert tracker.disturbances.config.turbulence_blur_sigma_px == 0.8
    assert tracker.disturbances.config.scintillation_log_std == 0.12
    assert tracker.disturbances.config.illumination_flicker_fraction == 0.08
    assert tracker.camera.gimbal.max_rate == 6.0
    assert tracker.camera.gimbal.max_tilt_rate == 6.0
    assert tracker.sim_time == 0.0


def test_invalid_preset_is_rejected_before_mutation(tmp_path):
    tracker = TrackingSystem()
    path = tmp_path / "unsafe.json"
    path.write_text(json.dumps({"target": {"size": 100}}), encoding="utf-8")

    with pytest.raises(PresetError, match="size must be between 5 and 20"):
        tracker.load_preset(str(path))
    assert tracker.primary_target.size == 10


def test_pan_and_tilt_limits_are_applied_independently():
    tracker = TrackingSystem()
    tracker.camera.set_rate_limits(7.0, 4.0)
    tracker.camera.gimbal.max_accel = 1000.0
    tracker.camera.apply_pan_tilt_command(20.0, 20.0, 0.1)
    assert tracker.camera.pan_velocity_deg_s == 7.0
    assert tracker.camera.tilt_velocity_deg_s == 4.0


def test_platform_jitter_preset_enables_bounded_stabilization_and_other_presets_reset_it():
    tracker = TrackingSystem()
    tracker.load_preset("archis_tracker/presets/platform_jitter.json")
    assert tracker.cam_config.inertial_stabilization_enabled
    assert tracker.cam_config.inertial_sensor_noise_px == 0.5
    tracker.load_preset("archis_tracker/presets/nominal_leo.json")
    assert not tracker.cam_config.inertial_stabilization_enabled


def test_platform_jitter_schema_migration_retains_inertial_configuration():
    scenario = load_scenario("archis_tracker/presets/platform_jitter.json")
    tracker = tracker_from_scenario(scenario)
    assert scenario.data["camera"]["inertial_stabilization_enabled"] is True
    assert tracker.cam_config.inertial_stabilization_enabled is True
    assert tracker.cam_config.inertial_sensor_noise_px == 0.5
