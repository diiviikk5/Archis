"""
Archis Optical Tracker - Real-time Telemetry Charts
High-performance dynamic strip charts using pyqtgraph for tracking error,
gimbal angles, system frame rates, and Jitter Power Spectral Density (FFT).
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget
import pyqtgraph as pg
import numpy as np
from collections import deque
from typing import Deque


class TelemetryChartsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        
        # Configure pyqtgraph global visual styling
        pg.setConfigOption('background', '#191a1c')
        pg.setConfigOption('foreground', '#9c9fa4')
        pg.setConfigOption('antialias', True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Tab 1: Tracking Error Chart
        self.plot_error = pg.PlotWidget(title="TRACKING ERROR (pixels) vs TIME")
        self.plot_error.showGrid(x=True, y=True, alpha=0.25)
        self.plot_error.setLabel('left', 'Error', units='px')
        self.plot_error.setLabel('bottom', 'Sim Time', units='s')
        self.curve_error = self.plot_error.plot(pen=pg.mkPen(color='#38bdf8', width=1.5))
        # 10px Specification reference line
        line_10px = pg.InfiniteLine(pos=10.0, angle=0, pen=pg.mkPen(color='#4ade80', width=1.2, style=pg.QtCore.Qt.PenStyle.DashLine))
        self.plot_error.addItem(line_10px)
        self.tabs.addTab(self.plot_error, "Tracking Error")
        
        # Tab 2: Gimbal Pan & Tilt Angles
        self.plot_gimbal = pg.PlotWidget(title="GIMBAL ANGLES (deg) vs TIME")
        self.plot_gimbal.showGrid(x=True, y=True, alpha=0.25)
        self.plot_gimbal.setLabel('left', 'Angle', units='deg')
        self.plot_gimbal.setLabel('bottom', 'Sim Time', units='s')
        self.plot_gimbal.addLegend(offset=(10, 10))
        self.curve_pan = self.plot_gimbal.plot(pen=pg.mkPen(color='#facc15', width=1.5), name="Pan (Azimuth)")
        self.curve_tilt = self.plot_gimbal.plot(pen=pg.mkPen(color='#a855f7', width=1.5), name="Tilt (Elevation)")
        self.tabs.addTab(self.plot_gimbal, "Gimbal Kinematics")
        
        # Tab 3: System FPS & Target Speed
        self.plot_perf = pg.PlotWidget(title="PROCESSING SPEED & TARGET VELOCITY")
        self.plot_perf.showGrid(x=True, y=True, alpha=0.25)
        self.plot_perf.setLabel('left', 'FPS / Speed')
        self.plot_perf.setLabel('bottom', 'Sim Time', units='s')
        self.plot_perf.addLegend(offset=(10, 10))
        self.curve_fps = self.plot_perf.plot(pen=pg.mkPen(color='#4ade80', width=1.5), name="FPS")
        self.curve_speed = self.plot_perf.plot(pen=pg.mkPen(color='#f43f5e', width=1.5), name="Target Speed (px/s)")
        self.tabs.addTab(self.plot_perf, "Performance & Speed")
        
        # Tab 4: Jitter Power Spectrum (FFT)
        self.plot_fft = pg.PlotWidget(title="JITTER & ERROR POWER SPECTRAL DENSITY (FFT)")
        self.plot_fft.showGrid(x=True, y=True, alpha=0.25)
        self.plot_fft.setLabel('left', 'Power (dB)')
        self.plot_fft.setLabel('bottom', 'Frequency', units='Hz')
        self.curve_fft = self.plot_fft.plot(pen=pg.mkPen(color='#ec4899', width=1.5), fillLevel=-40, fillBrush=pg.mkBrush(236, 72, 153, 50))
        self.tabs.addTab(self.plot_fft, "Jitter Spectrum (FFT)")
        for plot in (self.plot_error, self.plot_gimbal, self.plot_perf, self.plot_fft):
            plot.setTitle(None)
            plot.showGrid(x=False, y=True, alpha=0.12)
            plot.setMenuEnabled(False)
            plot.hideButtons()

    def clear_data(self):
        for curve in (self.curve_error, self.curve_pan, self.curve_tilt,
                      self.curve_fps, self.curve_speed, self.curve_fft):
            curve.clear()

    def update_data(self, times: Deque[float], errors: Deque[float],
                    pans: Deque[float], tilts: Deque[float],
                    fps_list: Deque[float], speeds: Deque[float]):
        """Feeds new rolling telemetry data points to pyqtgraph curves."""
        if len(times) < 2:
            return
            
        t_arr = np.array(times)
        current_idx = self.tabs.currentIndex()
        
        if current_idx == 0:
            self.curve_error.setData(t_arr, np.array(errors))
        elif current_idx == 1:
            self.curve_pan.setData(t_arr, np.array(pans))
            self.curve_tilt.setData(t_arr, np.array(tilts))
        elif current_idx == 2:
            self.curve_fps.setData(t_arr, np.array(fps_list))
            self.curve_speed.setData(t_arr, np.array(speeds))
        elif current_idx == 3:
            # Compute real-time FFT on last 128 error points
            err_arr = np.array(errors)
            if len(err_arr) >= 32:
                n = min(128, len(err_arr))
                segment = err_arr[-n:] - np.mean(err_arr[-n:])
                fft_vals = np.abs(np.fft.rfft(segment))
                period = float(np.median(np.diff(t_arr[-n:])))
                if period <= 0:
                    return
                freqs = np.fft.rfftfreq(n, d=period)
                # Convert to dB scale
                psd_db = 20.0 * np.log10(np.maximum(1e-3, fft_vals))
                self.curve_fft.setData(freqs, psd_db)
