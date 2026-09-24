"""Projection and detector evidence must expose real outcomes and readable files."""
from __future__ import annotations

import json

import cv2

from archis_tracker.core.config import TrackingAlgorithm
from archis_tracker.core.demo_evidence import (
    run_detector_robustness, run_geometry_validation,
    write_detector_robustness, write_geometry_validation,
)


def test_geometry_artifacts_measure_rendered_pixels_and_visibility(tmp_path):
    cases, _ = run_geometry_validation()
    assert {"center", "left edge", "top left corner", "outside FOV"} <= {case.name for case in cases}
    assert all(case.passed for case in cases)
    assert all(case.discrepancy_px <= .75 for case in cases if case.expected_visible)
    assert next(case for case in cases if case.name == "outside FOV").measured_x_px is None

    paths = write_geometry_validation(tmp_path)
    report = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert report["passed"] is True
    assert cv2.imread(str(paths["png"])).shape[0] > 100
    assert len(paths["csv"].read_text(encoding="utf-8").splitlines()) == len(cases) + 1


def test_detector_gallery_scores_misassociated_decoy_and_timing(tmp_path):
    cases, _ = run_detector_robustness(seed=26169, algorithm=TrackingAlgorithm.IWC)
    by_name = {case.name: case for case in cases}
    assert by_name["clean"].outcome == "TP"
    assert by_name["blank"].outcome == "TN"
    assert by_name["bright decoy"].outcome in {"TP", "FN+FP", "FN"}
    assert all(case.processing_time_ms >= 0 for case in cases)

    paths = write_detector_robustness(tmp_path, seed=26169, algorithm=TrackingAlgorithm.IWC)
    report = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert sum(report["counts"].values()) >= len(cases)
    assert report["scope"].startswith("cold single-frame")
    assert cv2.imread(str(paths["png"])).shape[1] >= 1000
