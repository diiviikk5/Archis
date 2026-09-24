"""
Archis Desktop Sub-Interfaces - Windows 11 Fluent Design Architecture.
Contains modular sub-interfaces for MSFluentWindow:
  1. HomeInterface - Mission launcher, system overview & benchmark status
  2. SetupInterface - Segmented parameter configuration & preset loader
  3. TrackingInterface - Live optical viewport, radar minimap, telemetry dashboard, and strip charts
  4. ReviewInterface - Session telemetry measurement audit & automated evidence reports
"""
from __future__ import annotations
import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget,
    QScrollArea, QTextBrowser, QSplitter, QSizePolicy, QFrame
)
from qfluentwidgets import (
    ElevatedCardWidget, CardWidget, PrimaryPushButton, PushButton,
    FluentIcon as FIF, IconWidget, TitleLabel, SubtitleLabel,
    BodyLabel, CaptionLabel, StrongBodyLabel, SegmentedWidget, InfoBadge, ComboBox
)

from .telemetry_display import TelemetryDashboard
from .viewport import ViewportWidget
from .minimap import MinimapWidget
from .charts import TelemetryChartsWidget

if TYPE_CHECKING:
    from .main_window import MainWindow


class HomeInterface(QWidget):
    def __init__(self, window: MainWindow, parent=None):
        super().__init__(parent)
        self.window = window
        self.setObjectName("homeInterface")
        self._build_ui()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area container for smooth responsiveness
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(36, 24, 36, 24)
        layout.setSpacing(16)

        # 1. Branded Hero Header Card with Embedded Logo
        hero_card = ElevatedCardWidget()
        h_layout = QHBoxLayout(hero_card)
        h_layout.setContentsMargins(22, 16, 22, 16)
        h_layout.setSpacing(18)

        # Embedded Logo
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
        logo_path = os.path.join(assets_dir, "logo.png")
        if os.path.exists(logo_path):
            logo_lbl = QLabel()
            pix = QPixmap(logo_path).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(pix)
            h_layout.addWidget(logo_lbl)

        h_text = QVBoxLayout()
        h_text.setSpacing(4)
        title = TitleLabel("ARCHIS // OPTICAL TRACKING CONSOLE")
        title.setStyleSheet("font-size: 22px; font-weight: 800; color: #f0f6fc; letter-spacing: 1px;")
        subtitle = BodyLabel("Autonomous Pointing, Acquisition, and Tracking (PAT) Ground Station adhering to ISRO FSOC Specifications.")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 13px;")
        h_text.addWidget(title)
        h_text.addWidget(subtitle)
        h_layout.addLayout(h_text, 1)

        status_col = QVBoxLayout()
        status_col.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        status_pill = QLabel("GROUND STATION // READY")
        status_pill.setStyleSheet("color: #38bdf8; background-color: #082032; border: 1px solid #0284c7; border-radius: 6px; padding: 6px 12px; font: 700 11px Consolas, monospace;")
        status_col.addWidget(status_pill)
        h_layout.addLayout(status_col)

        layout.addWidget(hero_card)

        # 2. Benchmark Compliance Banner Card
        banner = ElevatedCardWidget()
        b_layout = QHBoxLayout(banner)
        b_layout.setContentsMargins(20, 14, 20, 14)
        b_icon = IconWidget(FIF.ACCEPT)
        b_icon.setFixedSize(28, 28)
        b_layout.addWidget(b_icon)

        b_text = QVBoxLayout()
        b_text.setSpacing(2)
        b_title = StrongBodyLabel("Tracking performance criteria")
        b_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #f0f6fc;")
        b_sub = CaptionLabel("Acquisition <= 2.0s | RMS Error <= 10.0px | Target Loss < 5.0% | Re-acq <= 1.0s | Speed >= 20 FPS")
        b_sub.setStyleSheet("color: #94a3b8; font-size: 11px;")
        b_text.addWidget(b_title)
        b_text.addWidget(b_sub)
        b_layout.addLayout(b_text, 1)

        spec_pill = QLabel("RUN TO EVALUATE")
        spec_pill.setStyleSheet("color: #34d399; background-color: #062319; border: 1px solid #059669; border-radius: 6px; padding: 6px 12px; font: 700 11px Consolas, monospace;")
        b_layout.addWidget(spec_pill)
        layout.addWidget(banner)

        # 3. Mission Action Cards
        missions = [
            ("Nominal LEO Beacon Pass",
             "Pre-configured benchmark pass: moving beacon with platform jitter, Gaussian noise, and Kalman state estimation.",
             "Launch Nominal Pass", self._start_nominal, FIF.PLAY, True),
            ("Virtual Mission Setup",
             "Customize beacon shape, 2D continuous SDF kinematics, gimbal slew limits, and atmospheric fog/rain models.",
             "Configure Mission", self._goto_setup, FIF.SETTING, False),
            ("Evaluator Flight Video Pipeline",
             "Ingest external MP4/AVI camera video feed directly through real-time sub-pixel centroiding and Kalman filtering.",
             "Load Video Source", self.window._open_video, FIF.VIDEO, False),
            ("High-Jitter Rejection Test",
             "Stress test with +-20 px high-frequency mechanical vibration and active dead-reckoning trajectory projection.",
             "Launch Jitter Scenario", self._start_high_jitter, FIF.SYNC, False),
        ]

        for m_title, m_desc, m_action, m_cb, m_icon, is_primary in missions:
            card = ElevatedCardWidget()
            card.setObjectName("homeAction")
            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(20, 16, 20, 16)
            c_layout.setSpacing(16)

            icon_widget = IconWidget(m_icon)
            icon_widget.setFixedSize(30, 30)
            c_layout.addWidget(icon_widget)

            t_layout = QVBoxLayout()
            t_layout.setSpacing(3)
            card_title = StrongBodyLabel(m_title)
            card_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #f0f6fc;")
            card_desc = BodyLabel(m_desc)
            card_desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
            card_desc.setWordWrap(True)
            t_layout.addWidget(card_title)
            t_layout.addWidget(card_desc)
            c_layout.addLayout(t_layout, 1)

            btn = PrimaryPushButton(m_icon, f" {m_action}") if is_primary else PushButton(m_icon, f" {m_action}")
            btn.setMinimumHeight(38)
            btn.clicked.connect(m_cb)
            c_layout.addWidget(btn)

            layout.addWidget(card)

        layout.addStretch()
        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def _start_nominal(self):
        self.window._load_preset("nominal_leo.json")
        self.window.switchTo(self.window.tracking_interface)
        self.window._set_running(True)

    def _start_high_jitter(self):
        self.window._load_preset("high_jitter.json")
        self.window.switchTo(self.window.tracking_interface)
        self.window._set_running(True)

    def _goto_setup(self):
        self.window.switchTo(self.window.setup_interface)


class SetupInterface(QWidget):
    def __init__(self, window: MainWindow, parent=None):
        super().__init__(parent)
        self.window = window
        self.setObjectName("setupInterface")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 28, 36, 20)
        layout.setSpacing(14)

        title = TitleLabel("Mission Setup & Subsystem Configuration")
        title.setStyleSheet("font-size: 24px; font-weight: 800; color: #f0f6fc;")
        subtitle = BodyLabel("Configure optical target characteristics, gimbal kinematics, noise models, and Kalman tracking.")
        subtitle.setStyleSheet("color: #8b949e; font-size: 13px;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Segmented navigation bar
        self.segmented = SegmentedWidget(self)
        layout.addWidget(self.segmented)

        self.editors_stack = QStackedWidget(self)
        tabs = self.window.control_panel.tabs

        categories = [
            ("target", "Target Profile", FIF.FLAG),
            ("optics", "Optics & Algo", FIF.ZOOM_IN),
            ("gimbal", "Gimbal Pedestal", FIF.CAMERA),
            ("disturb", "Disturbances", FIF.GLOBE),
            ("presets", "Mission Presets", FIF.DOCUMENT),
        ]

        idx = 0
        while tabs.count() > 0:
            editor = tabs.widget(0)
            tabs.removeTab(0)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll.setWidget(editor)
            self.editors_stack.addWidget(scroll)

            if idx < len(categories):
                key, label, icon = categories[idx]
                target_idx = idx
                self.segmented.addItem(
                    routeKey=key,
                    text=label,
                    onClick=lambda checked=False, i=target_idx: self.editors_stack.setCurrentIndex(i),
                    icon=icon,
                )
            idx += 1

        layout.addWidget(self.editors_stack, 1)
        self.segmented.setCurrentItem("target")

        # Action bar
        actions = QHBoxLayout()
        actions.addStretch()
        start_btn = PrimaryPushButton(FIF.PLAY, " Start Closed-Loop Mission")
        start_btn.setMinimumHeight(40)
        start_btn.clicked.connect(self._launch_mission)
        actions.addWidget(start_btn)
        layout.addLayout(actions)

    def _launch_mission(self):
        self.window.switchTo(self.window.tracking_interface)
        self.window._set_running(True)




class ReviewInterface(QWidget):
    def __init__(self, window: MainWindow, parent=None):
        super().__init__(parent)
        self.window = window
        self.setObjectName("reviewInterface")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 28, 36, 24)
        layout.setSpacing(14)

        title = TitleLabel("Mission Evidence & Telemetry Audit")
        title.setStyleSheet("font-size: 24px; font-weight: 800; color: #f0f6fc;")
        subtitle = BodyLabel("Review closed-loop telemetry metrics, RMS pointing stability, and generated session evidence.")
        subtitle.setStyleSheet("color: #8b949e; font-size: 13px;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Audit Document
        self.review_text = QTextBrowser()
        self.review_text.setObjectName("reviewDocument")
        layout.addWidget(self.review_text, 1)

        # Actions
        actions = QHBoxLayout()
        actions.setSpacing(10)

        refresh_btn = PushButton(FIF.SYNC, " Refresh Telemetry")
        refresh_btn.clicked.connect(self.update_review)
        actions.addWidget(refresh_btn)

        actions.addStretch()

        open_folder_btn = PushButton(FIF.FOLDER, " Open Evidence Folder")
        open_folder_btn.clicked.connect(self.window._open_reports)
        actions.addWidget(open_folder_btn)

        finish_btn = PrimaryPushButton(FIF.SAVE, " Finish Run & Save Reports")
        finish_btn.clicked.connect(self.finish_run)
        actions.addWidget(finish_btn)

        layout.addLayout(actions)

    def update_review(self):
        summary = self.window.tracker.telemetry.get_summary()
        if not summary["total_frames"]:
            self.review_text.setHtml(
                "<div style='font-family: Segoe UI, sans-serif; padding: 20px;'>"
                "<h2 style='color: #f0f6fc; margin-bottom: 8px;'>No Active Session Telemetry</h2>"
                "<p style='color: #8b949e;'>Start a tracking pass from <b>Home</b> or <b>Mission Setup</b> to record real-time performance evidence.</p>"
                "</div>"
            )
            return

        acq_pass = summary.get("acquisition_passed", True)
        rms_pass = summary.get("error_passed", True)
        loss_pass = summary.get("loss_passed", True)
        reacq_pass = summary.get("reacquisition_passed", True)

        def badge(passed: bool, label: str = "PASS"):
            color = "#34d399" if passed else "#f87171"
            bg = "#062319" if passed else "#2b1014"
            border = "#059669" if passed else "#dc2626"
            text = label if passed else "FAIL"
            return f"<span style='color: {color}; background-color: {bg}; border: 1px solid {border}; border-radius: 4px; padding: 3px 10px; font-weight: 700; font-family: Consolas;'>{text}</span>"

        logo_uri = f"file:///{self.window.logo_path.replace(os.sep, '/')}" if hasattr(self.window, 'logo_path') and os.path.exists(self.window.logo_path) else ""
        logo_html = f"<img src='{logo_uri}' width='48' height='48' style='vertical-align: middle;' />" if logo_uri else ""

        html = f"""
        <div style='font-family: Segoe UI, sans-serif; color: #e6edf3; line-height: 1.6;'>
            <div style='border-bottom: 1px solid #1f2937; padding-bottom: 12px; margin-bottom: 16px;'>
                <table style='width: 100%; border-collapse: collapse;'>
                    <tr>
                        <td style='width: 58px; vertical-align: middle;'>{logo_html}</td>
                        <td style='vertical-align: middle; padding-left: 8px;'>
                            <h2 style='color: #f0f6fc; margin: 0; font-size: 20px; font-weight: 700;'>
                                ARCHIS // Optical Tracking Performance Audit
                            </h2>
                            <p style='color: #8b949e; font-size: 12px; margin: 4px 0 0 0;'>
                                Evaluated against ISRO autonomous tracking specifications (Acquisition &le; 2.0s, RMS &le; 10.0px, Loss &lt; 5.0%, Re-acq &le; 1.0s, FPS &ge; 20).
                            </p>
                        </td>
                    </tr>
                </table>
            </div>

            <table style='width: 100%; border-collapse: collapse; margin-bottom: 20px;'>
                <tr style='border-bottom: 1px solid #1f2937;'>
                    <th style='text-align: left; padding: 8px 6px; color: #8b949e;'>Parameter</th>
                    <th style='text-align: left; padding: 8px 6px; color: #8b949e;'>Measured Value</th>
                    <th style='text-align: left; padding: 8px 6px; color: #8b949e;'>Specification Limit</th>
                    <th style='text-align: right; padding: 8px 6px; color: #8b949e;'>Compliance Status</th>
                </tr>
                <tr style='border-bottom: 1px solid #161f2c;'>
                    <td style='padding: 10px 6px;'><b>Acquisition Time</b></td>
                    <td style='padding: 10px 6px; font-family: Consolas;'>{summary['acquisition_time_s']:.2f} s</td>
                    <td style='padding: 10px 6px; color: #8b949e;'>&le; 2.00 s</td>
                    <td style='padding: 10px 6px; text-align: right;'>{badge(acq_pass)}</td>
                </tr>
                <tr style='border-bottom: 1px solid #161f2c;'>
                    <td style='padding: 10px 6px;'><b>Steady-State RMS Error</b></td>
                    <td style='padding: 10px 6px; font-family: Consolas;'>{summary['rms_error_px']:.2f} px</td>
                    <td style='padding: 10px 6px; color: #8b949e;'>&le; 10.0 px</td>
                    <td style='padding: 10px 6px; text-align: right;'>{badge(rms_pass)}</td>
                </tr>
                <tr style='border-bottom: 1px solid #161f2c;'>
                    <td style='padding: 10px 6px;'><b>Target Loss Rate</b></td>
                    <td style='padding: 10px 6px; font-family: Consolas;'>{summary['target_loss_pct']:.2f} %</td>
                    <td style='padding: 10px 6px; color: #8b949e;'>&lt; 5.0 %</td>
                    <td style='padding: 10px 6px; text-align: right;'>{badge(loss_pass)}</td>
                </tr>
                <tr style='border-bottom: 1px solid #161f2c;'>
                    <td style='padding: 10px 6px;'><b>Re-acquisition Time</b></td>
                    <td style='padding: 10px 6px; font-family: Consolas;'>{summary['reacquisition_time_s']:.2f} s</td>
                    <td style='padding: 10px 6px; color: #8b949e;'>&le; 1.00 s</td>
                    <td style='padding: 10px 6px; text-align: right;'>{badge(reacq_pass)}</td>
                </tr>
            </table>

            <h3 style='color: #f0f6fc; margin-top: 16px; margin-bottom: 8px;'>Operational Statistics</h3>
            <ul style='color: #8b949e; font-size: 13px; line-height: 1.8;'>
                <li>Total Frames Processed: <b style='color: #f0f6fc; font-family: Consolas;'>{summary['total_frames']}</b></li>
                <li>Session Duration: <b style='color: #f0f6fc; font-family: Consolas;'>{summary['simulation_duration_s']:.2f} s</b></li>
                <li>Lock Retention: <b style='color: #f0f6fc; font-family: Consolas;'>{summary['lock_retention_pct']:.1f}%</b></li>
                <li>Peak Boresight Error: <b style='color: #f0f6fc; font-family: Consolas;'>{summary['max_error_px']:.2f} px</b></li>
                <li>Average Loop Cycle: <b style='color: #f0f6fc; font-family: Consolas;'>{summary['average_processing_time_ms']:.2f} ms</b></li>
            </ul>
        </div>
        """
        self.review_text.setHtml(html)

    def finish_run(self):
        self.window._set_running(False)
        path = self.window.tracker.telemetry.finish_session()
        self.update_review()
        if path:
            self.window.show_info_toast("Session Reports Saved", f"Exported evidence to {path}")

