import os
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import PrimaryPushButton, PushButton, FluentIcon as FIF


class OnboardingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.start_nominal = False
        self.setWindowTitle("Archis Quick Start Guide")
        self.setModal(True)
        self.setFixedWidth(560)
        self.setObjectName("onboardingDialog")

        assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
        logo_path = os.path.join(assets_dir, "logo.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # Header with embedded logo
        header_row = QHBoxLayout()
        header_row.setSpacing(14)
        if os.path.exists(logo_path):
            logo_lbl = QLabel()
            pix = QPixmap(logo_path).scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(pix)
            header_row.addWidget(logo_lbl)

        h_text = QVBoxLayout()
        h_text.setSpacing(2)
        eyebrow = QLabel("FIRST RUN & OPERATOR GUIDE")
        eyebrow.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: 700; letter-spacing: 1.5px;")
        title = QLabel("Autonomous Optical Beacon Lock")
        title.setStyleSheet("color: #f0f6fc; font-size: 18px; font-weight: 700;")
        h_text.addWidget(eyebrow)
        h_text.addWidget(title)
        header_row.addLayout(h_text, 1)
        layout.addLayout(header_row)

        copy = QLabel("Archis executes the complete optical tracking and pointing pipeline locally. Configure target kinematics, acquire the beacon, and export evidence from the same evaluation session.")
        copy.setStyleSheet("color: #94a3b8; font-size: 12px; line-height: 1.4;")
        copy.setWordWrap(True)
        layout.addWidget(copy)

        steps = (
            ("1", "Select Mission Scenario", "Load nominal LEO or customize 2D SDF shape, gimbal kinematics, noise, and atmospheric fog."),
            ("2", "Closed-Loop Acquisition", "Observe real-time IWC/Gaussian centroiding, Archimedean spiral search, and Kalman innovation gating."),
            ("3", "Verify Specification Evidence", "CSV telemetry logs, JSON parameters, and human-readable audit reports are recorded automatically."),
        )
        for number, heading, detail in steps:
            layout.addWidget(self._step(number, heading, detail))

        hint = QLabel("Keyboard: Space toggles Start/Pause | Ctrl+R resets the run | Click viewport to designate.")
        hint.setStyleSheet("color: #64748b; font-size: 11px; font-family: Consolas, monospace;")
        layout.addWidget(hint)

        actions = QHBoxLayout()
        actions.addStretch()
        explore = PushButton(FIF.HOME, " Open Console")
        explore.clicked.connect(self.accept)
        start = PrimaryPushButton(FIF.PLAY, " Start Nominal Mission")
        start.clicked.connect(self._start)
        actions.addWidget(explore)
        actions.addWidget(start)
        layout.addLayout(actions)

    def _step(self, number: str, heading: str, detail: str) -> QWidget:
        row = QWidget()
        row.setObjectName("onboardingStep")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        badge = QLabel(number)
        badge.setObjectName("stepBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(26, 26)
        text = QVBoxLayout()
        text.setSpacing(2)
        title = QLabel(heading)
        title.setObjectName("stepTitle")
        body = QLabel(detail)
        body.setObjectName("stepCopy")
        body.setWordWrap(True)
        text.addWidget(title)
        text.addWidget(body)
        layout.addWidget(badge)
        layout.addLayout(text, 1)
        return row

    def _start(self):
        self.start_nominal = True
        self.accept()
