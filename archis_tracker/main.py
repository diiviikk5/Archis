"""
Archis Optical Tracker - Standalone Desktop Software Application Entrypoint
Autonomous Virtual Camera Tracking System for Optical Beacon Acquisition and Tracking.
"""
import sys
import os
import argparse
import time

# Ensure package directory is in sys.path
if hasattr(sys, '_MEIPASS'):
    sys.path.insert(0, sys._MEIPASS)
else:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from archis_tracker.core.tracker import TrackingSystem
from archis_tracker.core.config import (TargetShape, MotionTrajectory, 
                                       AtmosphericCondition, PlatformMotionType)


def run_benchmark(duration_s: float = 10.0):
    """
    Runs automated headless benchmark against all 5 official specification criteria:
    1. Acquisition Time <= 2.0 s
    2. Tracking Error <= 10.0 pixels
    3. Target Loss < 5.0 %
    4. Re-acquisition Time <= 1.0 s
    5. Processing Speed >= 20 FPS
    """
    print("=" * 72)
    print("  ARCHIS FSOC OPTICAL TRACKER // AUTOMATED VERIFICATION BENCHMARK")
    print(f"  Simulating {duration_s:.1f}s of closed-loop tracking @ 30 Hz...")
    print("=" * 72)
    
    tracker = TrackingSystem()
    dt = 1.0 / 30.0
    total_steps = int(duration_s / dt)
    
    start_real = time.perf_counter()
    for step_idx in range(total_steps):
        tracker.step(dt)
        if step_idx % 60 == 0:
            print(f"  Step {step_idx:4d}/{total_steps} | State: {tracker.state.value:<25} | Error: {tracker.telemetry.current_error_px:4.1f} px | RMS: {tracker.telemetry.rms_error_px:4.1f} px")
            
    real_elapsed = time.perf_counter() - start_real
    real_fps = total_steps / max(1e-4, real_elapsed)
    
    summary = tracker.telemetry.get_summary()
    
    print("")
    print("=" * 72)
    print("  OFFICIAL SPECIFICATION VERIFICATION AUDIT RESULTS:")
    print("=" * 72)
    
    # 1. Acquisition Time
    acq_status = "PASSED [PASS]" if summary["acquisition_passed"] else "FAILED [FAIL]"
    print(f"  1. Acquisition Time:      {summary['acquisition_time_s']:6.2f} s   (Spec: <= 2.0 s)  -> {acq_status}")
    
    # 2. Tracking Error
    err_status = "PASSED [PASS]" if summary["error_passed"] else "FAILED [FAIL]"
    print(f"  2. Steady-State RMS Error: {summary['rms_error_px']:6.2f} px  (Spec: <= 10.0 px) -> {err_status}")
    
    # 3. Target Loss %
    loss_status = "PASSED [PASS]" if summary["loss_passed"] else "FAILED [FAIL]"
    print(f"  3. Target Loss Rate:      {summary['target_loss_pct']:6.2f} %   (Spec: < 5.0 %)   -> {loss_status}")
    
    # 4. Re-acquisition Time
    reacq_status = "PASSED [PASS]" if summary["reacquisition_passed"] else "FAILED [FAIL]"
    print(f"  4. Re-acquisition Time:   {summary['reacquisition_time_s']:6.2f} s   (Spec: <= 1.0 s)  -> {reacq_status}")
    
    # 5. Processing Speed
    fps_status = "PASSED [PASS]" if real_fps >= 20.0 else "FAILED [FAIL]"
    print(f"  5. Processing Speed:      {real_fps:6.1f} FPS (Spec: >= 20 FPS)  -> {fps_status}")
    
    print("=" * 72)
    all_passed = (summary["acquisition_passed"] and summary["error_passed"] and 
                  summary["loss_passed"] and summary["reacquisition_passed"] and real_fps >= 20.0)
    if all_passed:
        print("  VERDICT: ALL OFFICIAL SPECIFICATIONS MET WITH EXCELLENCE! [10/10]")
    else:
        print("  VERDICT: BENCHMARK COMPLETED WITH NOTED DEVIATIONS.")
    print("=" * 72)
    print("")
    return all_passed


def main():
    import traceback
    log_path = os.path.join(os.path.expanduser("~"), "archis_crash.log")
    try:
        with open(log_path, "a") as f:
            f.write(f"\n[{time.ctime()}] Starting Archis Tracker. MEIPASS: {getattr(sys, '_MEIPASS', 'None')}\n")
            
        parser = argparse.ArgumentParser(description="Archis FSOC Autonomous Optical Tracker")
        parser.add_argument("--benchmark", action="store_true", help="Run automated verification benchmark")
        parser.add_argument("--duration", type=float, default=8.0, help="Benchmark duration in seconds")
        parser.add_argument("--headless", action="store_true", help="Run headless simulation loop without GUI")
        args = parser.parse_args()
        
        if args.benchmark or args.headless:
            success = run_benchmark(duration_s=args.duration)
            sys.exit(0 if success else 1)
            
        # Launch PyQt6 GUI Application
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        from archis_tracker.ui.main_window import MainWindow
        
        app = QApplication(sys.argv)
        app.setApplicationName("Archis Optical Tracker")
        app.setOrganizationName("Archis FSOC")
        
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
