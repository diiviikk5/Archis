"""
Archis Optical Tracker - Telemetry Metrics Dashboard
Renders numerical cards, status indicators, and specification pass/fail badges.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt
from ..core.config import TrackingState, PerformanceThresholds


class TelemetryDashboard(QWidget):
    def __init__(self, thresholds: PerformanceThresholds, parent=None):
        super().__init__(parent)
        self.thresholds = thresholds
        
        main_layout = QGridLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)
        
        # 1. Tracking Error Card
        self.card_error = self._create_card("TRACKING ERROR", "0.0 px", "RMS: 0.0 px", "#38bdf8")
        main_layout.addWidget(self.card_error["frame"], 0, 0)
        
        # 2. Acquisition Performance Card
        self.card_acq = self._create_card("ACQUISITION TIME", "-- s", "Spec: <= 2.0 s", "#4ade80")
        main_layout.addWidget(self.card_acq["frame"], 0, 1)
        
        # 3. Target Loss Card
        self.card_loss = self._create_card("TARGET LOSS", "0.0 %", "Spec: < 5.0 %", "#4ade80")
        main_layout.addWidget(self.card_loss["frame"], 0, 2)
        
        # 4. Processing FPS Card
        self.card_fps = self._create_card("CYCLE RATE", "30.0 FPS", "Spec: >= 20 FPS", "#38bdf8")
        main_layout.addWidget(self.card_fps["frame"], 0, 3)

    def _create_card(self, title: str, main_val: str, sub_val: str, accent_color: str):
        frame = QFrame()
        frame.setObjectName("cardFrame")
        frame.setMinimumHeight(72)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 600; letter-spacing: 0.5px;")
        
        lbl_val = QLabel(main_val)
        lbl_val.setStyleSheet(f"color: {accent_color}; font-size: 18px; font-weight: 700; font-family: Consolas, monospace;")
        
        lbl_sub = QLabel(sub_val)
        lbl_sub.setStyleSheet("color: #64748b; font-size: 10px; font-family: Consolas, monospace;")
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        layout.addWidget(lbl_sub)
        
        return {"frame": frame, "title": lbl_title, "val": lbl_val, "sub": lbl_sub}

    def update_metrics(self, current_error: float, rms_error: float,
                       acq_time: float, has_acq: bool,
                       loss_pct: float, reacq_time: float,
                       fps: float, state: TrackingState):
        """Updates numerical cards with current values and pass/fail highlights."""
        # 1. Error
        err_color = "#4ade80" if current_error <= 10.0 else ("#facc15" if current_error <= 20.0 else "#f43f5e")
        self.card_error["val"].setText(f"{current_error:4.1f} px")
        self.card_error["val"].setStyleSheet(f"color: {err_color}; font-size: 18px; font-weight: 700; font-family: Consolas, monospace;")
        self.card_error["sub"].setText(f"RMS: {rms_error:4.1f} px (<=10 px {'PASS' if rms_error <= 10.0 else 'FAIL'})")
        
        # 2. Acquisition Time
        if has_acq:
            acq_pass = acq_time <= self.thresholds.max_acquisition_time_s
            acq_color = "#4ade80" if acq_pass else "#f43f5e"
            self.card_acq["val"].setText(f"{acq_time:4.2f} s")
            self.card_acq["val"].setStyleSheet(f"color: {acq_color}; font-size: 18px; font-weight: 700; font-family: Consolas, monospace;")
            self.card_acq["sub"].setText(f"Re-acq: {reacq_time:3.2f} s (<=1s PASS)")
        else:
            self.card_acq["val"].setText("ACQUIRING...")
            self.card_acq["val"].setStyleSheet("color: #facc15; font-size: 16px; font-weight: 700; font-family: Consolas, monospace;")
            
        # 3. Target Loss
        loss_pass = loss_pct < self.thresholds.max_target_loss_pct
        loss_color = "#4ade80" if loss_pass else "#f43f5e"
        self.card_loss["val"].setText(f"{loss_pct:3.1f} %")
        self.card_loss["val"].setStyleSheet(f"color: {loss_color}; font-size: 18px; font-weight: 700; font-family: Consolas, monospace;")
        self.card_loss["sub"].setText(f"Spec: < 5% ({'PASS' if loss_pass else 'FAIL'})")
        
        # 4. FPS
        fps_pass = fps >= self.thresholds.min_processing_fps
        fps_color = "#38bdf8" if fps_pass else "#f43f5e"
        self.card_fps["val"].setText(f"{fps:4.1f} FPS")
        self.card_fps["val"].setStyleSheet(f"color: {fps_color}; font-size: 18px; font-weight: 700; font-family: Consolas, monospace;")
        self.card_fps["sub"].setText(f"Spec: >= 20 FPS ({'PASS' if fps_pass else 'FAIL'})")
