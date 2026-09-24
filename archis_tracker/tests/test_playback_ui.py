"""Desktop pacing and viewport integration checks without a visible window."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PyQt6.QtWidgets import QApplication
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


def test_playback_preserves_sensor_period(window, monkeypatch):
    periods = []
    monkeypatch.setattr(window.tracker, "step", lambda dt: periods.append(dt))
    window.is_running = True
    for index, scale in enumerate((0.25, 0.5, 1.0)):
        window.tracking_interface.playback_speed.setCurrentIndex(index)
        window._simulation_tick()
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
