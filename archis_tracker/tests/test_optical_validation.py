from __future__ import annotations

from dataclasses import replace
import json

import numpy as np
import pytest

from archis_tracker.core.config import DetectorConfig, DisturbanceConfig, TrackingAlgorithm
from archis_tracker.core.contracts import GroundTruthSample
from archis_tracker.core.detector import BeaconDetector
from archis_tracker.core.disturbances import (
    DisturbanceEngine, gamma_gamma_parameters, sample_gamma_gamma_gain,
)
from archis_tracker.core.kalman_filter import KalmanFilter2D
from archis_tracker.core.performance import PerformanceRecorder
from archis_tracker.core.photometry import SpotPhotometry, measurement_sigma_px
from archis_tracker.core.scenario import DEFAULT_SCENARIO, Scenario, tracker_from_scenario, validate_scenario
from archis_tracker.core.tracker import TrackingSystem
from archis_tracker.core.validation import (
    calibrate_measurement_noise, mechanical_velocity_limit_px_s,
    run_optical_validation, run_velocity_envelope,
)


def test_optical_sweep_tracks_spot_scale_snr_and_saturation():
    rows = run_optical_validation(
        fwhm_values=(3.0, 15.0), noise_values=(1.0, 14.0),
        peak_values=(120.0, 360.0), phases=((.25, .75),),
    )
    assert len(rows) == 8 and all(row.detected for row in rows)
    small = [row.measured_fwhm_px for row in rows if row.requested_fwhm_px == 3.0]
    large = [row.measured_fwhm_px for row in rows if row.requested_fwhm_px == 15.0]
    assert np.median(large) > 3 * np.median(small)
    low_noise = [row.snr_aperture for row in rows if row.noise_std == 1.0 and row.requested_peak == 120]
    high_noise = [row.snr_aperture for row in rows if row.noise_std == 14.0 and row.requested_peak == 120]
    assert np.median(low_noise) > np.median(high_noise)
    assert max(row.saturated_fraction for row in rows if row.requested_peak == 360) > .05


def test_measurement_noise_is_bounded_and_penalizes_clipping():
    nominal = SpotPhotometry(8.0, 20.0, 30.0, 10.0, 2.0, False, 0.0)
    clipped = replace(nominal, clipped=True)
    assert measurement_sigma_px(nominal, calibration=14.2) == pytest.approx(2.84)
    assert measurement_sigma_px(clipped, calibration=14.2) > measurement_sigma_px(nominal, calibration=14.2)
    assert measurement_sigma_px(replace(nominal, snr_aperture=None)) == 20.0


def test_shipped_calibration_matches_reproducible_validation_matrix():
    rows = run_optical_validation()
    fitted = calibrate_measurement_noise(rows)
    assert fitted == pytest.approx(14.153717585045335, abs=.1)
    assert DetectorConfig().measurement_noise_calibration == pytest.approx(fitted, abs=.1)


def test_kalman_uses_optical_measurement_uncertainty():
    precise, noisy = KalmanFilter2D(), KalmanFilter2D()
    for item in (precise, noisy):
        item.reset(100, 100)
        item.predict(1 / 30)
    assert precise.update(102, 100, measurement_sigma_px=.2)
    assert noisy.update(102, 100, measurement_sigma_px=5.0)
    assert precise.last_measurement_sigma_px == .2
    assert noisy.last_measurement_sigma_px == 5.0
    assert precise.cov[0, 0] < noisy.cov[0, 0]


def test_detector_geometry_adapts_across_spot_scales():
    detector = BeaconDetector(DetectorConfig(algorithm=TrackingAlgorithm.IWC))
    measured = []
    yy, xx = np.indices((128, 128))
    for fwhm in (3.0, 7.0, 15.0):
        sigma = fwhm / 2.354820045
        frame = np.clip(10 + 230 * np.exp(-((xx - 64.4) ** 2 + (yy - 63.7) ** 2) / (2 * sigma * sigma)), 0, 255).astype(np.uint8)
        result = detector.detect(frame)
        assert result.detected and result.fwhm_px is not None
        measured.append(result.fwhm_px)
    assert measured[0] < measured[1] < measured[2]


def test_gamma_gamma_channel_is_repeatable_and_unit_mean():
    alpha, beta = gamma_gamma_parameters(.5)
    assert alpha > 0 and beta > 0
    first = np.random.default_rng(77)
    second = np.random.default_rng(77)
    a = [sample_gamma_gamma_gain(first, .5) for _ in range(5000)]
    b = [sample_gamma_gamma_gain(second, .5) for _ in range(5000)]
    assert a == b
    assert np.mean(a) == pytest.approx(1.0, abs=.05)

    config = DisturbanceConfig(random_seed=77, scintillation_model="gamma_gamma", rytov_variance=.5)
    engine_a, engine_b = DisturbanceEngine(config), DisturbanceEngine(config)
    frame = np.full((32, 32), 100, dtype=np.uint8)
    assert np.array_equal(engine_a.apply_disturbances_to_frame(frame), engine_b.apply_disturbances_to_frame(frame))


def test_scenario_validates_and_builds_new_optical_controls():
    raw = json.loads(json.dumps(DEFAULT_SCENARIO))
    raw["disturbances"].update(scintillation_model="gamma_gamma", rytov_variance=.6)
    raw["detector"].update(fallback_fwhm_px=9.0, measurement_noise_calibration=12.0)
    scenario = Scenario(validate_scenario(raw))
    tracker = tracker_from_scenario(scenario)
    assert tracker.disturb_config.scintillation_model == "gamma_gamma"
    assert tracker.disturb_config.rytov_variance == .6
    assert tracker.det_config.fallback_fwhm_px == 9.0
    assert tracker.det_config.measurement_noise_calibration == 12.0
    bad = json.loads(json.dumps(DEFAULT_SCENARIO))
    bad["detector"]["minimum_fwhm_px"] = 20
    bad["detector"]["maximum_fwhm_px"] = 10
    with pytest.raises(ValueError):
        validate_scenario(bad)


def test_reports_include_photometry_and_conservative_p95_throughput(tmp_path):
    tracker = TrackingSystem(det_config=DetectorConfig(algorithm=TrackingAlgorithm.IWC))
    recorder = PerformanceRecorder("latency", (128, 128))
    frame = np.zeros((128, 128), dtype=np.uint8)
    frame[61:68, 61:68] = 255
    for latency in (1.0, 2.0, 3.0, 4.0, 100.0):
        tracker.step_external_frame(frame, 1 / 30, GroundTruthSample(64, 64))
        recorder.record(replace(tracker.last_result, processing_time_ms=latency), tracker.last_truth, 30)
    summary = recorder.summary()
    assert summary.processing_p50_ms == 3.0
    assert summary.processing_p95_ms == pytest.approx(80.8)
    assert summary.conservative_processing_fps == pytest.approx(1000 / 80.8)
    assert not summary.fps_passed
    payload = json.loads(recorder.export(tmp_path)["json"].read_text(encoding="utf-8"))
    assert payload["frames"][-1]["fwhm_px"] is not None
    assert payload["frames"][-1]["measurement_sigma_px"] is not None


def test_velocity_envelope_is_finite_and_mechanically_bounded():
    scenario = Scenario(validate_scenario(json.loads(json.dumps(DEFAULT_SCENARIO))))
    assert mechanical_velocity_limit_px_s(scenario) == 800.0
    payload = run_velocity_envelope(scenario, speeds_px_s=(40.0, 160.0, 900.0), frames=30)
    assert payload["tested_maximum_px_s"] == 160.0
    assert payload["bounded_trackable_velocity_px_s"] <= payload["mechanical_limit_px_s"]
    assert len(payload["rows"]) == 2
