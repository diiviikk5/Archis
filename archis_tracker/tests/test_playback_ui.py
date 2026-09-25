"""Desktop pacing and viewport integration checks without a visible window."""
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
import json
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from archis_tracker.core.config import AtmosphericCondition
from archis_tracker.ui.main_window import MainWindow


@pytest.fixture
def window(monkeypatch, tmp_path, qt_app):
    monkeypatch.setattr(MainWindow, "_show_onboarding", lambda self: None)
    monkeypatch.setattr(
        "archis_tracker.ui.main_window.QStandardPaths.writableLocation",
        lambda location: str(tmp_path),
    )
    widget = MainWindow()
    widget.sim_timer.stop()
    yield widget
    widget.close()
    qt_app.processEvents()


@pytest.fixture(scope="session")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def test_playback_preserves_sensor_period(window, monkeypatch, qt_app):
    periods = []
    monkeypatch.setattr(window.tracker, "step", lambda dt: periods.append(dt))
    window.is_running = True
    for index, scale in enumerate((0.25, 0.5, 1.0)):
        window.tracking_interface.playback_speed.setCurrentIndex(index)
        window._simulation_tick()
        deadline = time.monotonic() + 1.0
        while window.worker_busy and time.monotonic() < deadline:
            qt_app.processEvents()
            time.sleep(0.001)
        assert not window.worker_busy
        assert window.sim_timer.interval() == round(
            1000 / window.tracker.cam_config.update_rate_hz / scale
        )
    assert periods == [1 / window.tracker.cam_config.update_rate_hz] * 3


def test_viewport_uses_actual_frame_dimensions(window):
    viewport = window.viewport
    viewport.update_frame(
        np.zeros((240, 800), dtype=np.uint8), None, 400, 120,
        window.tracker.state, 0, 0, 30, 0, 0, 0,
    )
    assert (viewport.frame_width, viewport.frame_height) == (800, 240)
    assert not viewport.grab().isNull()


def test_overlay_controls_do_not_change_sensor_frame(window):
    live = window.tracking_interface
    window._simulation_tick()
    before = live.viewport.frame_image.copy()
    for attribute, checkbox in live.overlay_controls.items():
        checkbox.setChecked(not checkbox.isChecked())
        assert getattr(live.viewport, attribute) == checkbox.isChecked()
    assert live.viewport.frame_image == before


def test_capture_writes_real_frame(window, monkeypatch, tmp_path):
    window._simulation_tick()
    path = tmp_path / 'sensor.png'
    monkeypatch.setattr('archis_tracker.ui.live_workspace.QFileDialog.getSaveFileName',
                        lambda *args: (str(path), 'PNG'))
    window.tracking_interface._capture()
    assert path.read_bytes().startswith(b'\x89PNG')


def test_turbulence_controls_update_live_configuration(window):
    panel = window.control_panel
    panel.spin_turbulence_warp.setValue(4.5)
    panel.spin_turbulence_blur.setValue(0.9)
    panel.spin_scintillation.setValue(0.14)
    panel.spin_illumination.setValue(0.07)
    panel.spin_illumination_hz.setValue(2.5)
    config = window.tracker.disturb_config
    assert config.turbulence_warp_px == 4.5
    assert config.turbulence_blur_sigma_px == 0.9
    assert config.scintillation_log_std == 0.14
    assert config.illumination_flicker_fraction == 0.07
    assert config.illumination_flicker_hz == 2.5


def test_navigation_summary_shows_live_configuration(window):
    summary = window.scenario_summary
    assert "Deterministic simulation" in summary.field_text("Input")
    assert "2000×2000" in summary.field_text("Environment")
    assert "TX range 1000 m" in summary.field_text("Terminals")
    assert window.tracker.primary_target.shape.value in summary.field_text("Target")
    assert window.tracker.detector.config.algorithm.value in summary.field_text("Detector")


def test_navigation_summary_refreshes_after_configuration_changes(window):
    config = window.tracker.disturb_config
    config.atmospheric_condition = AtmosphericCondition.FOG
    config.atmospheric_severity = 0.8
    config.enable_gaussian_noise = True
    config.gaussian_noise_std = 13.0
    window.tracker.primary_target.config.range_m = 4250.0
    window.tracker._refresh_world_snapshot()

    window.scenario_summary.refresh()
    assert "Fog 80%" in window.scenario_summary.field_text("Environment")
    assert "Gaussian σ13" in window.scenario_summary.field_text("Disturbances")
    assert "TX range 4250 m" in window.scenario_summary.field_text("Terminals")


def test_navigation_summary_discloses_active_inertial_stabilization(window):
    window.tracker.cam_config.inertial_stabilization_enabled = True
    window.tracker.cam_config.inertial_sensor_noise_px = 0.5
    window.scenario_summary.refresh()
    assert "inertial stabilizer ON (σ0.5px)" in window.scenario_summary.field_text("Camera")


def test_navigation_summary_collapses_without_reserving_empty_space(window):
    summary = window.scenario_summary
    summary.setCompacted(True)
    assert summary.size().width() == 40
    assert summary.size().height() == 36
    assert summary.content.isHidden()
    summary.setCompacted(False)
    assert not summary.content.isHidden()
    assert summary.size().height() == summary.EXPANDED_HEIGHT


def test_all_chart_legends_are_below_the_plot_area(window):
    charts = window.tracking_interface.charts
    expected_labels = (
        (charts.plot_error, {"Pointing offset", "Centroid error"}),
        (charts.plot_gimbal, {"Pan (Azimuth)", "Tilt (Elevation)"}),
        (charts.plot_perf, {"Source FPS", "Processing FPS", "Target Speed (px/s)"}),
        (charts.plot_fft, {"Pointing-error spectrum"}),
    )
    for plot, labels in expected_labels:
        item = plot.getPlotItem()
        assert item.layout.itemAt(4, 1) is item.legend
        assert {label.text for _, label in item.legend.items} == labels


def test_split_world_sensor_and_judge_modes_keep_visual_context(window):
    live = window.tracking_interface
    window._simulation_tick()
    assert live.view_mode.currentText() == "Split"
    assert not live.camera_panel.isHidden()
    assert not live.world_panel.isHidden()
    assert window.minimap.world_model.snapshot is not None

    live.view_mode.setCurrentText("World")
    assert live.camera_panel.isHidden()
    assert not live.world_panel.isHidden()
    live.view_mode.setCurrentText("Judge")
    assert not live.camera_panel.isHidden()
    assert not live.world_panel.isHidden()
    assert live.inspector.isHidden()
    assert live.charts.isHidden()
    live.view_mode.setCurrentText("Split")
    assert not live.inspector.isHidden()


def test_demo_capture_writes_synchronized_views_and_active_config(window):
    detection = window.tracker.step(1 / 30)
    window._render_tracking(detection)
    paths = window._capture_demo_evidence()
    assert paths["sensor"].read_bytes().startswith(b"\x89PNG")
    assert paths["world"].read_bytes().startswith(b"\x89PNG")
    assert paths["split"].read_bytes().startswith(b"\x89PNG")
    payload = json.loads(paths["metadata"].read_text(encoding="utf-8"))
    assert payload["frame_index"] == window.tracker.frame_index
    assert payload["configuration"]["environment"]["screen_width"] == 2000
    assert payload["images"] == ["sensor_view.png", "world_view.png", "world_sensor.png"]


def test_review_has_empty_state_and_refreshes_on_navigation(window, qt_app):
    review = window.review_interface
    assert review.review_stack.currentWidget() is review.empty_state

    window.show()
    window.switchTo(window.tracking_interface)
    window.tracker.step(1 / 30)
    window.switchTo(review)
    qt_app.processEvents()
    assert review.review_stack.currentWidget() is review.review_text
    assert "ARCHIS // Optical Tracking Performance Audit" in review.review_text.toPlainText()
    assert "Not evaluated" in review.review_text.toPlainText()


def test_review_actions_fit_minimum_and_default_window_width(window, qt_app):
    window.show()
    window.switchTo(window.review_interface)
    for width in (1160, 1500):
        window.resize(width, 740)
        qt_app.processEvents()
        for button in window.review_interface.action_buttons.values():
            assert button.width() >= button.sizeHint().width(), (
                width, button.text(), button.width(), button.sizeHint().width()
            )
    # FluentWindow slides between pages; assert visibility after the animation.
    QTest.qWait(500)
    for button in window.review_interface.action_buttons.values():
        assert button.mapTo(window, button.rect().bottomLeft()).y() < window.height()
