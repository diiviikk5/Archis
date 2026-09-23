"""
Archis Optical Tracker - Standalone Desktop Software Application Entrypoint
Autonomous Virtual Camera Tracking System for Optical Beacon Acquisition and Tracking.
"""
import sys
import os
import argparse
import time
from dataclasses import asdict
from copy import deepcopy
import json

# Ensure package directory is in sys.path
if hasattr(sys, '_MEIPASS'):
    sys.path.insert(0, sys._MEIPASS)
else:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from archis_tracker.resources import user_data_dir


def run_benchmark(duration_s: float = 10.0, algorithm_name: str | None = None,
                  scenario_path: str | None = None):
    """Run the same scenario-driven benchmark used by the ``archis`` CLI."""
    from archis_tracker.cli import _run_scenario
    from archis_tracker.core.config import TrackingAlgorithm
    from archis_tracker.core.scenario import Scenario, load_scenario, validate_scenario

    path = scenario_path or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "presets", "cloud_dropout.json"
    )
    loaded = load_scenario(path)
    data = deepcopy(dict(loaded.data))
    data["evaluation"]["duration_s"] = duration_s
    if algorithm_name:
        matches = [item for item in TrackingAlgorithm if (
            algorithm_name.lower() in item.name.lower()
            or algorithm_name.lower() in item.value.lower()
        )]
        if not matches:
            raise ValueError(f"unknown tracking algorithm: {algorithm_name}")
        data["detector"]["algorithm"] = matches[0].name
    scenario = Scenario(validate_scenario(data), loaded.path)
    frames = round(duration_s * float(data["camera"]["update_hz"]))
    _, recorder = _run_scenario(scenario, frames)
    report_dir = user_data_dir() / "Reports" / f"benchmark_{int(time.time())}"
    paths = recorder.export(report_dir)
    summary = recorder.summary()
    print(json.dumps(asdict(summary), indent=2))
    for kind, output in paths.items():
        print(f"{kind.upper()}: {output}")
    return summary.passed


def main():
    import traceback
    log_path = str(user_data_dir() / "archis_crash.log")
    try:
        with open(log_path, "a") as f:
            f.write(f"\n[{time.ctime()}] Starting Archis Tracker. MEIPASS: {getattr(sys, '_MEIPASS', 'None')}\n")
            
        cli_commands = {
            "validate", "simulate", "track", "record", "analyze", "benchmark",
            "compare", "stress-test", "train-ai",
        }
        if len(sys.argv) > 1 and sys.argv[1] in cli_commands:
            from archis_tracker.cli import main as cli_main
            raise SystemExit(cli_main(sys.argv[1:]))

        parser = argparse.ArgumentParser(description="Archis FSOC Autonomous Optical Tracker")
        parser.add_argument("--benchmark", action="store_true", help="Run automated verification benchmark")
        parser.add_argument("--duration", type=float, default=60.0, help="Benchmark duration in seconds")
        parser.add_argument("--algorithm", type=str, default=None, help="Algorithm to benchmark (ai, gaussian, iwc, ncc)")
        parser.add_argument("--scenario", type=str, default=None, help="Scenario or legacy preset JSON")
        parser.add_argument("--headless", action="store_true", help="Run headless simulation loop without GUI")
        args = parser.parse_args()
        
        if args.benchmark or args.headless:
            success = run_benchmark(
                duration_s=args.duration,
                algorithm_name=args.algorithm,
                scenario_path=args.scenario,
            )
            sys.exit(0 if success else 1)
            
        # Launch PyQt6 GUI Application
        import ctypes
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Archis.FSOC.OpticalTracker.2.0")
        except Exception:
            pass

        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont, QIcon
        from PyQt6.QtCore import Qt
        from archis_tracker.ui.main_window import MainWindow

        app = QApplication(sys.argv)
        app.setApplicationName("Archis Optical Tracker")
        app.setOrganizationName("Archis FSOC")

        # Crisp, anti-aliased Segoe UI typography across the desktop environment
        app_font = QFont("Segoe UI", 10)
        app_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        app.setFont(app_font)

        # Set application and taskbar icon
        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        logo_path = os.path.join(assets_dir, "logo.png")
        if os.path.exists(logo_path):
            app.setWindowIcon(QIcon(logo_path))

        window = MainWindow()
        window.show()
        
        with open(log_path, "a") as f:
            f.write(f"[{time.ctime()}] Window displayed, entering event loop...\n")
            
        code = app.exec()
        with open(log_path, "a") as f:
            f.write(f"[{time.ctime()}] app.exec() exited with code: {code}\n")
        sys.exit(code)
    except Exception as e:
        with open(log_path, "a") as f:
            f.write(f"[{time.ctime()}] CRITICAL EXCEPTION:\n{traceback.format_exc()}\n")
        raise


if __name__ == "__main__":
    main()
