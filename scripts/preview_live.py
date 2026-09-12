"""Render reproducible desktop captures using the actual Qt widgets and tracker."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('QT_QPA_PLATFORM', 'windows' if '--native' in sys.argv else 'offscreen')
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from archis_tracker.ui.main_window import MainWindow
from archis_tracker.core.config import TrackingAlgorithm

app = QApplication([])
app.setFont(QFont('Segoe UI', 10))
output = Path('work/live-preview')
output.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as reports, patch.object(MainWindow, 'show_success_toast', lambda *args: None), patch.object(MainWindow, '_show_onboarding', lambda self: None), patch(
    'archis_tracker.ui.main_window.QStandardPaths.writableLocation', return_value=reports
):
    window = MainWindow()
    window.sim_timer.stop()
    window.tracker.detector.config.algorithm = TrackingAlgorithm.AI_ONNX
    window.tracking_interface.viewport.show_heatmap = True
    window.tracking_interface.overlay_controls['show_heatmap'].setChecked(True)
    window.is_running = True
    window.switchTo(window.tracking_interface)
    for _ in range(100):
        window._simulation_tick()
    window.is_running = False
    window._update_run_state()
    for width, height in ((1160, 740), (1500, 940), (1920, 1080)):
        window.resize(width, height)
        window.show()
        app.processEvents()
        window.grab().save(str(output / f'live-{width}.png'))
        live = window.tracking_interface
        print(width, height, 'viewport', live.viewport.size(), 'inspector', live.inspector.size(), flush=True)
    window.close()
