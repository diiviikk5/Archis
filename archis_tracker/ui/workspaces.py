"""Task-oriented desktop navigation and run review."""
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QListWidget,
    QStackedWidget, QScrollArea, QTextBrowser, QStyle,
)


def heading(layout, title, detail):
    label = QLabel(title)
    label.setObjectName("pageTitle")
    layout.addWidget(label)
    subtitle = QLabel(detail)
    subtitle.setObjectName("pageSubtitle")
    subtitle.setWordWrap(True)
    layout.addWidget(subtitle)


def button(text, callback, primary=False):
    item = QPushButton(text)
    item.setObjectName("primaryButton" if primary else "secondaryButton")
    item.clicked.connect(callback)
    return item


class DesktopWorkspaces(QWidget):
    def __init__(self, window, live):
        super().__init__()
        self.window = window
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        sidebar = QWidget()
        sidebar.setObjectName("navigationRail")
        sidebar.setFixedWidth(200)
        rail = QVBoxLayout(sidebar)
        rail.setContentsMargins(12, 24, 12, 16)
        logo = QLabel("ARCHIS")
        logo.setObjectName("railBrand")
        rail.addWidget(logo)
        caption = QLabel("Optical tracking")
        caption.setObjectName("pageSubtitle")
        rail.addWidget(caption)
        rail.addSpacing(24)
        self.navigation = QListWidget()
        self.navigation.setObjectName("workspaceNavigation")
        self.navigation.addItems(["Home", "Mission setup", "Live tracking", "Run review"])
        rail.addWidget(self.navigation)
        rail.addWidget(button("Quick start", window._show_onboarding))
        rail.addWidget(button("Reports folder", window._open_reports))
        root.addWidget(sidebar)
        self.pages = QStackedWidget()
        root.addWidget(self.pages, 1)
        self.pages.addWidget(self.home())
        self.pages.addWidget(self.setup())
        self.pages.addWidget(live)
        self.pages.addWidget(self.review())
        self.navigation.currentRowChanged.connect(self.navigate)
        self.navigation.setCurrentRow(0)

    def navigate(self, index):
        self.pages.setCurrentIndex(index)
        if self.navigation.currentRow() != index:
            self.navigation.setCurrentRow(index)
        if index == 3:
            self.update_review()

    def home(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(48, 40, 48, 32)
        heading(layout, "Your tracking workspace", "Start a mission or evaluate a recorded beacon pass.")
        layout.addSpacing(24)
        for title, detail, action, callback, icon in (
            ("Virtual mission", "Configure a beacon, camera and atmospheric conditions.", "Set up mission", lambda: self.navigate(1), QStyle.StandardPixmap.SP_ComputerIcon),
            ("Recorded video", "Evaluate a local MP4 with the optical tracking pipeline.", "Open video", self.window._open_video, QStyle.StandardPixmap.SP_MediaPlay),
            ("Nominal mission", "Clear-sky preset with a moving beacon and camera jitter.", "Start nominal mission", self.start_nominal, QStyle.StandardPixmap.SP_DialogApplyButton),
        ):
            row = QWidget()
            row.setObjectName("homeAction")
            content = QHBoxLayout(row)
            content.setContentsMargins(0, 22, 0, 22)
            symbol = QLabel()
            symbol.setPixmap(self.style().standardIcon(icon).pixmap(32, 32))
            content.addWidget(symbol)
            text = QVBoxLayout()
            label = QLabel(title)
            label.setObjectName("sectionTitle")
            text.addWidget(label)
            description = QLabel(detail)
            description.setWordWrap(True)
            description.setObjectName("pageSubtitle")
            text.addWidget(description)
            content.addLayout(text, 1)
            content.addWidget(button(action, callback))
            layout.addWidget(row)
        layout.addStretch()
        return page

    def start_nominal(self):
        self.window._load_preset("nominal_leo.json")
        self.window._set_running(True)

    def setup(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 24)
        heading(layout, "Mission setup", "Configure the next acquisition.")
        body = QHBoxLayout()
        categories = QListWidget()
        categories.setObjectName("setupNavigation")
        categories.setFixedWidth(160)
        categories.addItems(["Target", "Detection", "Camera control", "Environment", "Scenarios"])
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
        actions.addWidget(button("Start mission", lambda: self.window._set_running(True), True))
        layout.addLayout(actions)
        return page

    def review(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 24)
        heading(layout, "Run review", "Measurements and saved evidence from the current session.")
        self.review_text = QTextBrowser()
        self.review_text.setObjectName("reviewDocument")
        layout.addWidget(self.review_text, 1)
        actions = QHBoxLayout()
        actions.addWidget(button("Refresh measurements", self.update_review))
        actions.addStretch()
        actions.addWidget(button("Open evidence folder", self.window._open_reports))
        actions.addWidget(button("Finish run and save reports", self.finish_run, True))
        layout.addLayout(actions)
        return page

    def update_review(self):
        summary = self.window.tracker.telemetry.get_summary()
        if not summary["total_frames"]:
            self.review_text.setHtml("<h2>No measurements yet</h2><p>Start a mission from Home or Mission setup.</p>")
            return
        rows = [("Frames", str(summary["total_frames"])),
                ("Duration", f"{summary['simulation_duration_s']:.2f} s"),
                ("Mean pointing error", f"{summary['average_error_px']:.2f} px"),
                ("Maximum pointing error", f"{summary['max_error_px']:.2f} px"),
                ("Lock retention", f"{summary['lock_retention_pct']:.2f}%"),
                ("Processing time", f"{summary['average_processing_time_ms']:.2f} ms")]
        self.review_text.setHtml("<h2>Session measurements</h2><table cellspacing='16'>" +
            "".join(f"<tr><td>{name}</td><td><b>{value}</b></td></tr>" for name, value in rows) +
            "</table><p>Pointing errors are relative to the camera boresight. Ground-truth centroid scoring is not available in this view.</p>")

    def finish_run(self):
        self.window._set_running(False)
        path = self.window.tracker.telemetry.finish_session()
        self.update_review()
        if path:
            self.window.status_bar.showMessage(f"Reports saved to {path}")
