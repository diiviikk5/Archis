"""First-run operator onboarding dialog."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class OnboardingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.start_nominal = False
        self.setWindowTitle("Quick start")
        self.setModal(True)
        self.setFixedWidth(540)
        self.setObjectName("onboardingDialog")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(12)
        eyebrow = QLabel("FIRST RUN")
        eyebrow.setObjectName("dialogEyebrow")
        title = QLabel("Bring the beacon into lock.")
        title.setObjectName("dialogTitle")
        copy = QLabel("Archis runs the complete optical tracking pipeline locally. Configure a mission, acquire the beacon, and review evidence from the same run.")
        copy.setObjectName("dialogCopy")
        copy.setWordWrap(True)
        layout.addWidget(eyebrow)
        layout.addWidget(title)
        layout.addWidget(copy)
        steps = (
            ("1", "Choose conditions", "Load a scenario, then tune target motion, atmosphere, noise, and jitter."),
            ("2", "Start acquisition", "The camera feed and measurements come from the live tracking engine."),
            ("3", "Review evidence", "CSV, JSON, and readable performance reports are saved automatically."),
        )
        for number, heading, detail in steps:
            layout.addWidget(self._step(number, heading, detail))
        hint = QLabel("Tip: press Space to start or pause. Press Ctrl+R to reset the run.")
        hint.setObjectName("dialogHint")
        layout.addWidget(hint)
        actions = QHBoxLayout()
        actions.addStretch()
        explore = QPushButton("Open console")
        explore.setObjectName("secondaryButton")
        explore.clicked.connect(self.accept)
        start = QPushButton("Start nominal mission")
        start.setObjectName("primaryButton")
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
