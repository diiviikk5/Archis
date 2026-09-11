"""
Archis Optical Tracker - Telemetry Metrics Dashboard.
Renders Fluent elevated cards, status indicators, and specification pass/fail badges.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel
from PyQt6.QtCore import Qt
from qfluentwidgets import ElevatedCardWidget, InfoBadge
from ..core.config import TrackingState, PerformanceThresholds


class TelemetryDashboard(QWidget):
    def __init__(self, thresholds: PerformanceThresholds, parent=None):
        super().__init__(parent)
        self.thresholds = thresholds

        main_layout = QGridLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        # 1. Tracking Error Card
        self.card_error = self._create_fluent_card("TRACKING ERROR", "0.0 px", "RMS: 0.0 px", "#38bdf8", "SPEC <= 10 px")
        main_layout.addWidget(self.card_error["card"], 0, 0)

        # 2. Acquisition Performance Card
        self.card_acq = self._create_fluent_card("ACQUISITION TIME", "-- s", "Spec: <= 2.0 s", "#34d399", "SPEC <= 2.0 s")
        main_layout.addWidget(self.card_acq["card"], 0, 1)

        # 3. Target Loss Card
        self.card_loss = self._create_fluent_card("TARGET LOSS", "0.0 %", "Spec: < 5.0 %", "#34d399", "SPEC < 5.0 %")
        main_layout.addWidget(self.card_loss["card"], 0, 2)

        # 4. Processing FPS Card
        self.card_fps = self._create_fluent_card("CYCLE RATE", "30.0 FPS", "Spec: >= 20 FPS", "#38bdf8", "SPEC >= 20 FPS")
        main_layout.addWidget(self.card_fps["card"], 0, 3)

    def _create_fluent_card(self, title: str, main_val: str, sub_val: str, accent_color: str, badge_text: str):
        card = ElevatedCardWidget()
        card.setMinimumHeight(86)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 700; letter-spacing: 0.8px;")
        top_row.addWidget(lbl_title)
        top_row.addStretch()

        badge = QLabel(badge_text)
        badge.setStyleSheet("color: #94a3b8; background-color: #0f172a; border: 1px solid #1e293b; border-radius: 4px; padding: 3px 8px; font: 700 10px Consolas, monospace;")
        top_row.addWidget(badge)

        lbl_val = QLabel(main_val)
        lbl_val.setStyleSheet(f"color: {accent_color}; font-size: 22px; font-weight: 800; font-family: Consolas, monospace;")

        lbl_sub = QLabel(sub_val)
        lbl_sub.setStyleSheet("color: #94a3b8; font-size: 11px; font-family: Consolas, monospace;")

        layout.addLayout(top_row)
        layout.addWidget(lbl_val)
        layout.addWidget(lbl_sub)

        return {"card": card, "title": lbl_title, "val": lbl_val, "sub": lbl_sub, "badge": badge}

    def update_metrics(self, current_error: float, rms_error: float,
                       acq_time: float, has_acq: bool,
                       loss_pct: float, reacq_time: float,
                       fps: float, state: TrackingState):
        """Updates numerical cards with current values and pass/fail highlights."""
        # 1. Error
        err_color = "#34d399" if current_error <= 10.0 else ("#f59e0b" if current_error <= 20.0 else "#f87171")
        self.card_error["val"].setText(f"{current_error:4.1f} px")
        self.card_error["val"].setStyleSheet(f"color: {err_color}; font-size: 20px; font-weight: 800; font-family: Consolas, monospace;")
        err_passed = rms_error <= 10.0
        self.card_error["sub"].setText(f"RMS: {rms_error:4.1f} px ({'PASS' if err_passed else 'DEVIATION'})")
        self.card_error["badge"].setText("PASS" if err_passed else "FAIL")
        self.card_error["badge"].setStyleSheet(f"color: {'#34d399' if err_passed else '#f87171'}; background-color: {'#062319' if err_passed else '#2b1014'}; border: 1px solid {'#059669' if err_passed else '#dc2626'}; border-radius: 4px; padding: 2px 6px; font: 700 9px Consolas, monospace;")

        # 2. Acquisition Time
        if has_acq:
            acq_pass = acq_time <= self.thresholds.max_acquisition_time_s
            acq_color = "#34d399" if acq_pass else "#f87171"
            self.card_acq["val"].setText(f"{acq_time:4.2f} s")
            self.card_acq["val"].setStyleSheet(f"color: {acq_color}; font-size: 20px; font-weight: 800; font-family: Consolas, monospace;")
            self.card_acq["sub"].setText(f"Re-acq: {reacq_time:3.2f} s (<=1s PASS)")
            self.card_acq["badge"].setText("LOCKED" if acq_pass else "SLOW")
            self.card_acq["badge"].setStyleSheet(f"color: {'#34d399' if acq_pass else '#f87171'}; background-color: {'#062319' if acq_pass else '#2b1014'}; border: 1px solid {'#059669' if acq_pass else '#dc2626'}; border-radius: 4px; padding: 2px 6px; font: 700 9px Consolas, monospace;")
        else:
            self.card_acq["val"].setText("ACQUIRING...")
            self.card_acq["val"].setStyleSheet("color: #f59e0b; font-size: 17px; font-weight: 800; font-family: Consolas, monospace;")
            self.card_acq["badge"].setText("ACQUIRING")
            self.card_acq["badge"].setStyleSheet("color: #f59e0b; background-color: #261b0a; border: 1px solid #d97706; border-radius: 4px; padding: 2px 6px; font: 700 9px Consolas, monospace;")

        # 3. Target Loss
        loss_pass = loss_pct < self.thresholds.max_target_loss_pct
        loss_color = "#34d399" if loss_pass else "#f87171"
        self.card_loss["val"].setText(f"{loss_pct:3.1f} %")
        self.card_loss["val"].setStyleSheet(f"color: {loss_color}; font-size: 20px; font-weight: 800; font-family: Consolas, monospace;")
        self.card_loss["sub"].setText(f"Spec: < 5.0% ({'PASS' if loss_pass else 'FAIL'})")
        self.card_loss["badge"].setText("PASS" if loss_pass else "LOSS HIGH")
        self.card_loss["badge"].setStyleSheet(f"color: {'#34d399' if loss_pass else '#f87171'}; background-color: {'#062319' if loss_pass else '#2b1014'}; border: 1px solid {'#059669' if loss_pass else '#dc2626'}; border-radius: 4px; padding: 2px 6px; font: 700 9px Consolas, monospace;")

        # 4. FPS
        fps_pass = fps >= self.thresholds.min_processing_fps
        fps_color = "#38bdf8" if fps_pass else "#f87171"
        self.card_fps["val"].setText(f"{fps:4.1f} FPS")
        self.card_fps["val"].setStyleSheet(f"color: {fps_color}; font-size: 20px; font-weight: 800; font-family: Consolas, monospace;")
        self.card_fps["sub"].setText(f"Spec: >= 20 FPS ({'PASS' if fps_pass else 'FAIL'})")
        self.card_fps["badge"].setText("OPTIMAL" if fps >= 30.0 else ("PASS" if fps_pass else "DEGRADED"))
        self.card_fps["badge"].setStyleSheet(f"color: {'#38bdf8' if fps_pass else '#f87171'}; background-color: {'#082032' if fps_pass else '#2b1014'}; border: 1px solid {'#0284c7' if fps_pass else '#dc2626'}; border-radius: 4px; padding: 2px 6px; font: 700 9px Consolas, monospace;")
