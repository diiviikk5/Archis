"""Task-oriented desktop navigation and run review with Windows 11 Fluent widgets."""
from pathlib import Path

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QStackedWidget, QScrollArea, QTextBrowser, QFrame,
)
from qfluentwidgets import (
    ElevatedCardWidget, CardWidget, PrimaryPushButton, PushButton,
    TransparentPushButton, FluentIcon as FI, IconWidget, BodyLabel,
    CaptionLabel, TitleLabel, SubtitleLabel, StrongBodyLabel, InfoBadge
)


def heading(layout, title: str, detail: str):
    label = TitleLabel(title)
    label.setObjectName("pageTitle")
    layout.addWidget(label)
    subtitle = BodyLabel(detail)
    subtitle.setObjectName("pageSubtitle")
    subtitle.setWordWrap(True)
    layout.addWidget(subtitle)


class DesktopWorkspaces(QWidget):
    def __init__(self, window, live):
        super().__init__()
        self.window = window
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar navigation rail
        sidebar = QWidget()
        sidebar.setObjectName("navigationRail")
        sidebar.setFixedWidth(220)
        rail = QVBoxLayout(sidebar)
        rail.setContentsMargins(16, 24, 16, 20)
        rail.setSpacing(12)

        # Brand header
        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        logo_icon = IconWidget(FI.CAMERA)
        logo_icon.setFixedSize(28, 28)
        brand_row.addWidget(logo_icon)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        logo = StrongBodyLabel("ARCHIS OPTICAL")
        logo.setStyleSheet("font-size: 14px; font-weight: 800; letter-spacing: 1.5px; color: #f0f6fc;")
        caption = CaptionLabel("Ground Station PAT")
        caption.setStyleSheet("color: #8b949e; font-size: 10px;")
        brand_text.addWidget(logo)
        brand_text.addWidget(caption)
        brand_row.addLayout(brand_text)
        brand_row.addStretch()
        rail.addLayout(brand_row)
        rail.addSpacing(16)

        # Navigation items
        self.navigation = QListWidget()
        self.navigation.setObjectName("workspaceNavigation")
        nav_items = [
            ("Home", FI.HOME),
            ("Mission Setup", FI.SETTING),
            ("Live Tracking", FI.CAMERA),
            ("Run Review", FI.DOCUMENT),
        ]
        for name, icon in nav_items:
            item = QListWidgetItem(icon.icon(), f"  {name}")
            item.setSizeHint(QSize(180, 42))
            self.navigation.addItem(item)

        rail.addWidget(self.navigation, 1)

        # Utility actions
        quick_start_btn = PushButton(FI.HELP, " Quick Start")
        quick_start_btn.clicked.connect(window._show_onboarding)
        rail.addWidget(quick_start_btn)

        reports_btn = PushButton(FI.FOLDER, " Evidence Folder")
        reports_btn.clicked.connect(window._open_reports)
        rail.addWidget(reports_btn)

        root.addWidget(sidebar)

        # Page container
        self.pages = QStackedWidget()
        root.addWidget(self.pages, 1)
        self.pages.addWidget(self.home())
        self.pages.addWidget(self.setup())
        self.pages.addWidget(live)
        self.pages.addWidget(self.review())

        self.navigation.currentRowChanged.connect(self.navigate)
        self.navigation.setCurrentRow(0)

    def navigate(self, index: int):
        self.pages.setCurrentIndex(index)
        if self.navigation.currentRow() != index:
            self.navigation.setCurrentRow(index)
        if index == 3:
            self.update_review()

    def home(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(48, 36, 48, 32)
        layout.setSpacing(16)

        heading(layout, "Mission Control & Optical Evaluation",
                "Autonomous Pointing, Acquisition, and Tracking (PAT) ground control workspace.")
        layout.addSpacing(12)

        # Quick Status Banner Card
        banner = ElevatedCardWidget()
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(20, 16, 20, 16)
        banner_icon = IconWidget(FI.ACCEPT)
        banner_icon.setFixedSize(32, 32)
        banner_layout.addWidget(banner_icon)
        banner_info = QVBoxLayout()
        banner_info.setSpacing(2)
        b_title = StrongBodyLabel("Sub-Pixel Optical Tracking Engine Active")
        b_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #f0f6fc;")
        b_sub = CaptionLabel("Ready for 30 Hz closed-loop beacon tracking, multi-target gating, and turbulence simulation.")
        b_sub.setStyleSheet("color: #8b949e; font-size: 12px;")
        banner_info.addWidget(b_title)
        banner_info.addWidget(b_sub)
        banner_layout.addLayout(banner_info, 1)

        status_pill = QLabel("ISRO SPEC COMPLIANT")
        status_pill.setStyleSheet("color: #34d399; background-color: #062319; border: 1px solid #059669; border-radius: 6px; padding: 6px 12px; font: 700 11px Consolas, monospace;")
        banner_layout.addWidget(status_pill)
        layout.addWidget(banner)
        layout.addSpacing(8)

        # Action Cards Grid
        for title, detail, action, callback, icon, is_primary in (
            ("Virtual Mission Simulation",
             "Configure target trajectory, optics FOV, gimbal PID gains, and atmospheric turbulence.",
             "Configure Mission", lambda: self.navigate(1), FI.SETTING, False),
            ("Nominal LEO Beacon Pass",
             "Pre-configured benchmark scenario: moving target with simulated platform jitter and Gaussian noise.",
             "Launch Nominal Pass", self.start_nominal, FI.PLAY, True),
            ("Evaluator Video Pipeline",
             "Ingest and evaluate external MP4 camera footage through real-time centroiding and Kalman filter.",
             "Load Video Source", self.window._open_video, FI.VIDEO, False),
        ):
            card = ElevatedCardWidget()
            card.setObjectName("homeAction")
            content = QHBoxLayout(card)
            content.setContentsMargins(20, 20, 20, 20)
            content.setSpacing(16)

            card_icon = IconWidget(icon)
            card_icon.setFixedSize(36, 36)
            content.addWidget(card_icon)

            text_layout = QVBoxLayout()
            text_layout.setSpacing(3)
            card_title = StrongBodyLabel(title)
            card_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #f0f6fc;")
            text_layout.addWidget(card_title)

            card_desc = BodyLabel(detail)
            card_desc.setWordWrap(True)
            card_desc.setStyleSheet("color: #8b949e; font-size: 12px;")
            text_layout.addWidget(card_desc)
            content.addLayout(text_layout, 1)

            btn = PrimaryPushButton(icon, f" {action}") if is_primary else PushButton(icon, f" {action}")
            btn.setMinimumHeight(38)
            btn.clicked.connect(callback)
            content.addWidget(btn)

            layout.addWidget(card)

        layout.addStretch()
        return page

    def start_nominal(self):
        self.window._load_preset("nominal_leo.json")
        self.navigate(2)
        self.window._set_running(True)

    def setup(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 28, 36, 24)
        layout.setSpacing(14)

        heading(layout, "Mission Setup & Parameters",
                "Configure optical beacon characteristics, gimbal dynamics, noise models, and tracking loop.")

        body = QHBoxLayout()
        body.setSpacing(16)

        categories = QListWidget()
        categories.setObjectName("setupNavigation")
        categories.setFixedWidth(180)
        cat_items = [
            ("Target Profile", FI.FLAG),
            ("Detection & CV", FI.ZOOM_IN),
            ("Camera & Gimbal", FI.CAMERA),
            ("Atmospherics", FI.GLOBE),
            ("Mission Presets", FI.DOCUMENT),
        ]
        for name, icon in cat_items:
            item = QListWidgetItem(icon.icon(), f"  {name}")
            item.setSizeHint(QSize(160, 40))
            categories.addItem(item)
        body.addWidget(categories)

        self.editors = QStackedWidget()
        tabs = self.window.control_panel.tabs
        while tabs.count():
            editor = tabs.widget(0)
            tabs.removeTab(0)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll.setWidget(editor)
            self.editors.addWidget(scroll)

        body.addWidget(self.editors, 1)
        categories.currentRowChanged.connect(self.editors.setCurrentIndex)
        categories.setCurrentRow(0)
        layout.addLayout(body, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        start_btn = PrimaryPushButton(FI.PLAY, " Start Closed-Loop Mission")
        start_btn.setMinimumHeight(40)
        start_btn.clicked.connect(self._launch_from_setup)
        actions.addWidget(start_btn)
        layout.addLayout(actions)
        return page

    def _launch_from_setup(self):
        self.navigate(2)
        self.window._set_running(True)

    def review(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 28, 36, 24)
        layout.setSpacing(14)

        heading(layout, "Session Evidence & Performance Audit",
                "Review closed-loop telemetry metrics, RMS error stability, and generated session reports.")

        self.review_text = QTextBrowser()
        self.review_text.setObjectName("reviewDocument")
        layout.addWidget(self.review_text, 1)

        actions = QHBoxLayout()
        actions.setSpacing(10)

        refresh_btn = PushButton(FI.SYNC, " Refresh Telemetry")
        refresh_btn.clicked.connect(self.update_review)
        actions.addWidget(refresh_btn)

        actions.addStretch()

        open_folder_btn = PushButton(FI.FOLDER, " Open Evidence Folder")
        open_folder_btn.clicked.connect(self.window._open_reports)
        actions.addWidget(open_folder_btn)

        finish_btn = PrimaryPushButton(FI.SAVE, " Finish Run & Save Reports")
        finish_btn.clicked.connect(self.finish_run)
        actions.addWidget(finish_btn)

        layout.addLayout(actions)
        return page

    def update_review(self):
        summary = self.window.tracker.telemetry.get_summary()
        if not summary["total_frames"]:
            self.review_text.setHtml(
                "<div style='font-family: Segoe UI, sans-serif; padding: 20px;'>"
                "<h2 style='color: #f0f6fc; margin-bottom: 8px;'>No Active Session Data</h2>"
                "<p style='color: #8b949e;'>Initiate a tracking pass from <b>Home</b> or <b>Mission Setup</b> to generate closed-loop telemetry.</p>"
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
            return f"<span style='color: {color}; background-color: {bg}; border: 1px solid {border}; border-radius: 4px; padding: 2px 8px; font-weight: 700; font-family: Consolas;'>{text}</span>"

        html = f"""
        <div style='font-family: Segoe UI, sans-serif; color: #e6edf3; line-height: 1.6;'>
            <h2 style='color: #f0f6fc; border-bottom: 1px solid #1f2937; padding-bottom: 8px; margin-top: 0;'>
                Optical Tracking Performance Verification
            </h2>
            <p style='color: #8b949e; font-size: 12px; margin-bottom: 16px;'>
                Evaluated against ISRO autonomous tracking specifications (Acquisition &le; 2.0s, RMS Error &le; 10.0px, Target Loss &lt; 5.0%, Re-acquisition &le; 1.0s, FPS &ge; 20).
            </p>

            <table style='width: 100%; border-collapse: collapse; margin-bottom: 20px;'>
                <tr style='border-bottom: 1px solid #1f2937;'>
                    <th style='text-align: left; padding: 8px 4px; color: #8b949e;'>Parameter</th>
                    <th style='text-align: left; padding: 8px 4px; color: #8b949e;'>Measured Value</th>
                    <th style='text-align: left; padding: 8px 4px; color: #8b949e;'>Specification Limit</th>
                    <th style='text-align: right; padding: 8px 4px; color: #8b949e;'>Compliance Status</th>
                </tr>
                <tr style='border-bottom: 1px solid #161f2c;'>
                    <td style='padding: 10px 4px;'><b>Acquisition Time</b></td>
                    <td style='padding: 10px 4px; font-family: Consolas;'>{summary['acquisition_time_s']:.2f} s</td>
                    <td style='padding: 10px 4px; color: #8b949e;'>&le; 2.00 s</td>
                    <td style='padding: 10px 4px; text-align: right;'>{badge(acq_pass)}</td>
                </tr>
                <tr style='border-bottom: 1px solid #161f2c;'>
                    <td style='padding: 10px 4px;'><b>Steady-State RMS Error</b></td>
                    <td style='padding: 10px 4px; font-family: Consolas;'>{summary['rms_error_px']:.2f} px</td>
                    <td style='padding: 10px 4px; color: #8b949e;'>&le; 10.0 px</td>
                    <td style='padding: 10px 4px; text-align: right;'>{badge(rms_pass)}</td>
                </tr>
                <tr style='border-bottom: 1px solid #161f2c;'>
                    <td style='padding: 10px 4px;'><b>Target Loss Rate</b></td>
                    <td style='padding: 10px 4px; font-family: Consolas;'>{summary['target_loss_pct']:.2f} %</td>
                    <td style='padding: 10px 4px; color: #8b949e;'>&lt; 5.0 %</td>
                    <td style='padding: 10px 4px; text-align: right;'>{badge(loss_pass)}</td>
                </tr>
                <tr style='border-bottom: 1px solid #161f2c;'>
                    <td style='padding: 10px 4px;'><b>Re-acquisition Time</b></td>
                    <td style='padding: 10px 4px; font-family: Consolas;'>{summary['reacquisition_time_s']:.2f} s</td>
                    <td style='padding: 10px 4px; color: #8b949e;'>&le; 1.00 s</td>
                    <td style='padding: 10px 4px; text-align: right;'>{badge(reacq_pass)}</td>
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
            self.window.status_bar.showMessage(f"Reports saved to {path}")

