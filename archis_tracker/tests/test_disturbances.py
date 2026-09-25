"""Unit tests for Noise, Atmospheric Disturbance, and Jitter."""
import pytest
import numpy as np
import cv2
from archis_tracker.core.disturbances import DisturbanceEngine
from archis_tracker.core.config import DisturbanceConfig, AtmosphericCondition, PlatformMotionType


def test_image_noise_injections():
    # 1. Salt & Pepper
    cfg_sp = DisturbanceConfig(enable_salt_pepper=True, salt_pepper_ratio=0.1)
    eng_sp = DisturbanceEngine(cfg_sp)
    frame = np.full((480, 640), 100, dtype=np.uint8)
    noisy_sp = eng_sp.apply_disturbances_to_frame(frame)
    assert np.any(noisy_sp == 0) or np.any(noisy_sp == 255)

    # 2. Gaussian Noise
    cfg_gauss = DisturbanceConfig(enable_gaussian_noise=True, gaussian_noise_std=15.0)
    eng_gauss = DisturbanceEngine(cfg_gauss)
    noisy_gauss = eng_gauss.apply_disturbances_to_frame(frame)
    diff = np.abs(noisy_gauss.astype(np.float32) - 100.0)
    assert np.mean(diff) > 2.0, "Gaussian noise should perturb intensity"


def test_camera_jitter_and_platform_bounds():
    cfg = DisturbanceConfig(
        enable_camera_jitter=True, max_camera_jitter_px=20.0,
        enable_platform_motion=True, platform_motion_amplitude_px=20.0
    )
    eng = DisturbanceEngine(cfg)
    
    for _ in range(60):
        (jx, jy), (px, py) = eng.update(1.0 / 30.0)
        assert abs(jx) <= 20.0, "Jitter must not exceed +-20px"
        assert abs(jy) <= 20.0
        assert abs(px) <= 20.0, "Platform motion must not exceed +-20px"
        assert abs(py) <= 20.0


def test_atmospheric_conditions():
    for cond in AtmosphericCondition:
        cfg = DisturbanceConfig(atmospheric_condition=cond, atmospheric_severity=0.7)
        eng = DisturbanceEngine(cfg)
        frame = np.full((480, 640), 150, dtype=np.uint8)
        processed = eng.apply_disturbances_to_frame(frame)
        assert processed.shape == (480, 640)


def test_turbulence_and_scintillation_are_seeded_and_repeatable():
    config = DisturbanceConfig(
        random_seed=17,
        turbulence_warp_px=3.0,
        turbulence_blur_sigma_px=0.8,
        scintillation_log_std=0.15,
        illumination_flicker_fraction=0.1,
        illumination_flicker_hz=3.0,
    )
    first, second = DisturbanceEngine(config), DisturbanceEngine(config)
    frame = np.zeros((120, 160), dtype=np.uint8)
    frame[45:75, 65:95] = 220
    for _ in range(4):
        first.update(1 / 30)
        second.update(1 / 30)
        first_frame = first.apply_disturbances_to_frame(frame)
        second_frame = second.apply_disturbances_to_frame(frame)
        assert np.array_equal(first_frame, second_frame)
    assert not np.array_equal(first_frame, frame)


def test_turbulence_controls_are_independent():
    frame = np.zeros((80, 120), dtype=np.uint8)
    frame[30:50, 50:70] = 255
    base = DisturbanceEngine(DisturbanceConfig())
    base.update(0.1)
    assert np.array_equal(base.apply_disturbances_to_frame(frame), frame)

    warped = DisturbanceEngine(DisturbanceConfig(turbulence_warp_px=4.0))
    warped.update(0.1)
    assert not np.array_equal(warped.apply_disturbances_to_frame(frame), frame)


def test_burst_dropout_is_seeded_repeatable_and_resettable():
    config = DisturbanceConfig(
        random_seed=834,
        dropout_burst_enabled=True,
        dropout_mean_clear_s=0.08,
        dropout_mean_loss_s=0.06,
    )
    first, second = DisturbanceEngine(config), DisturbanceEngine(config)
    first_sequence, second_sequence = [], []
    for _ in range(180):
        first.update(1 / 30)
        second.update(1 / 30)
        first_sequence.append(first.is_dropout_active())
        second_sequence.append(second.is_dropout_active())

    assert first_sequence == second_sequence
    assert any(first_sequence) and not all(first_sequence)

    first.reset()
    replay = []
    for _ in range(180):
        first.update(1 / 30)
        replay.append(first.is_dropout_active())
    assert replay == first_sequence


def test_scheduled_and_burst_dropout_share_one_status_api():
    scheduled = DisturbanceEngine(DisturbanceConfig(
        dropout_enabled=True, dropout_start_s=0.1, dropout_duration_s=0.2,
    ))
    scheduled.update(0.09)
    assert not scheduled.is_dropout_active()
    scheduled.update(0.02)
    assert scheduled.is_dropout_active()
    scheduled.update(0.2)
    assert not scheduled.is_dropout_active()


def test_inertial_measurements_are_seeded_and_do_not_advance_image_noise_rng():
    config = DisturbanceConfig(random_seed=91, enable_gaussian_noise=True)
    measured = DisturbanceEngine(config)
    baseline = DisturbanceEngine(config)
    first = measured.measure_platform_offset(15.0, -4.0, 0.5)
    assert first != (15.0, -4.0)
    frame = np.full((32, 32), 100, dtype=np.uint8)
    assert np.array_equal(
        measured.apply_disturbances_to_frame(frame),
        baseline.apply_disturbances_to_frame(frame),
    )
    measured.reset()
    assert measured.measure_platform_offset(15.0, -4.0, 0.5) == first


def test_optimized_turbulence_matches_reference_float32_phase_screen():
    engine = DisturbanceEngine(DisturbanceConfig(random_seed=17, turbulence_warp_px=3.5))
    engine.update(1 / 30)
    frame = np.arange(120 * 160, dtype=np.uint32).reshape(120, 160).astype(np.uint8)
    grid_x, grid_y = engine._grid(*frame.shape)
    sin_a, cos_a, sin_b, cos_b, sin_c, cos_c, sin_d, cos_d = engine._turbulence_basis(*frame.shape)
    t, warp = engine.time_elapsed, 3.5
    dx = warp * (0.65 * (sin_a * np.cos(4.1 * t) + cos_a * np.sin(4.1 * t))
                 + 0.35 * (sin_b * np.cos(2.3 * t) - cos_b * np.sin(2.3 * t)))
    dy = warp * (0.65 * (cos_c * np.cos(3.7 * t) - sin_c * np.sin(3.7 * t))
                 + 0.35 * (cos_d * np.cos(2.9 * t) - sin_d * np.sin(2.9 * t)))
    reference = cv2.remap(frame.astype(np.float32),
                          (grid_x + dx).astype(np.float32), (grid_y + dy).astype(np.float32),
                          cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
    actual = engine.apply_disturbances_to_frame(frame)
    assert np.array_equal(actual, np.clip(reference, 0, 255).astype(np.uint8))
