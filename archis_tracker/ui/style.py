"""Archis desktop design system."""

DARK_THEME_QSS = """
QMainWindow, QDialog, QWidget {
    background-color: #090c10;
    color: #e8edf3;
    font-family: "Segoe UI";
    font-size: 12px;
}
QFrame#appHeader {
    min-height: 56px;
    max-height: 56px;
    background-color: #0d1116;
    border-bottom: 1px solid #29323d;
}
QLabel#brandMark {
    background-color: #45c7d8;
    color: #061014;
    border-radius: 5px;
    font-size: 18px;
    font-weight: 800;
}
QLabel#brandTitle { font-size: 16px; font-weight: 800; letter-spacing: 2px; }
QLabel#brandSubtitle { color: #929eab; font-size: 9px; letter-spacing: 1px; }
QLabel#terminalLabel { color: #929eab; font: 10px Consolas; }
QLabel#engineBadge {
    color: #5dd39e;
    background-color: #13221d;
    border: 1px solid #285843;
    border-radius: 4px;
    padding: 6px 9px;
    font: 700 9px Consolas;
}
QFrame#headerDivider { color: #29323d; }
QFrame#phaseStrip {
    min-height: 34px;
    max-height: 34px;
    background-color: #10151b;
    border-bottom: 1px solid #29323d;
}
QLabel#phaseIdle, QLabel#phaseActive {
    color: #697684;
    border-right: 1px solid #29323d;
    font: 700 9px Consolas;
}
QLabel#phaseActive { color: #76e0ec; background-color: #111e24; }
QWidget#missionPanel { background-color: #10151b; }
QWidget#centerWorkspace { background-color: #0b0f14; }
QSplitter#workspaceSplitter::handle, QSplitter#opticalSplitter::handle { background-color: #29323d; width: 1px; }

QFrame#cardFrame {
    background-color: #11171e;
    border: 1px solid #29323d;
    border-radius: 5px;
}
QGroupBox {
    background-color: #11171e;
    border: 1px solid #29323d;
    border-radius: 5px;
    margin-top: 13px;
    padding-top: 13px;
    color: #929eab;
    font-size: 10px;
    font-weight: 650;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 5px;
    background-color: #11171e;
    color: #e8edf3;
}
QTabWidget::pane { border: 1px solid #29323d; background-color: #10151b; top: -1px; }
QTabBar::tab {
    min-height: 30px;
    padding: 0 10px;
    background-color: #0d1116;
    color: #929eab;
    border: 1px solid #29323d;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    font-size: 10px;
}
QTabBar::tab:selected { color: #e8edf3; background-color: #151b22; border-bottom: 2px solid #45c7d8; }
QTabBar::tab:hover:!selected { background-color: #1b232c; color: #e8edf3; }

QPushButton {
    min-height: 34px;
    padding: 0 12px;
    background-color: #151b22;
    color: #e8edf3;
    border: 1px solid #3a4654;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 650;
}
QPushButton:hover { background-color: #1b232c; border-color: #607184; }
QPushButton:pressed { background-color: #10151b; }
QPushButton:focus { border: 2px solid #76e0ec; }
QPushButton#primaryButton, QPushButton#actionButton {
    min-height: 38px;
    background-color: #45c7d8;
    color: #061014;
    border-color: #45c7d8;
    font-weight: 750;
}
QPushButton#primaryButton:hover, QPushButton#actionButton:hover { background-color: #76e0ec; }
QPushButton#primaryButton[running="true"] { background-color: #e6ad55; border-color: #e6ad55; }
QPushButton#secondaryButton { background-color: #151b22; }
QPushButton:disabled { color: #697684; background-color: #11171e; border-color: #29323d; }

QComboBox, QSpinBox, QDoubleSpinBox {
    min-height: 34px;
    padding: 0 9px;
    background-color: #151b22;
    color: #e8edf3;
    border: 1px solid #3a4654;
    border-radius: 4px;
}
QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover { border-color: #45c7d8; }
QComboBox QAbstractItemView { background-color: #151b22; color: #e8edf3; selection-background-color: #26343e; outline: 0; }
QCheckBox { min-height: 28px; spacing: 8px; color: #c4cdd6; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #607184; border-radius: 3px; background: #151b22; }
QCheckBox::indicator:checked { background-color: #45c7d8; border-color: #45c7d8; }
QSlider::groove:horizontal { height: 4px; background: #29323d; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #45c7d8; border-radius: 2px; }
QSlider::handle:horizontal { width: 14px; margin: -6px 0; background: #e8edf3; border: 1px solid #697684; border-radius: 7px; }
QSlider::handle:horizontal:hover { background: #76e0ec; }

QStatusBar { min-height: 25px; max-height: 25px; background: #0d1116; color: #929eab; border-top: 1px solid #29323d; font-size: 10px; }
QStatusBar::item { border: none; }
QScrollBar:vertical { width: 8px; border: none; background: #0d1116; }
QScrollBar::handle:vertical { min-height: 24px; background: #3a4654; border-radius: 4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QDialog#onboardingDialog { background-color: #151b22; }
QLabel#dialogEyebrow { color: #45c7d8; font: 700 10px Consolas; letter-spacing: 2px; }
QLabel#dialogTitle { color: #e8edf3; font-size: 26px; font-weight: 750; }
QLabel#dialogCopy { color: #aab5c0; font-size: 12px; line-height: 1.4; }
QWidget#onboardingStep { background-color: #10151b; border: 1px solid #29323d; border-radius: 4px; }
QLabel#stepBadge { color: #76e0ec; border: 1px solid #3a6e76; border-radius: 13px; font: 700 10px Consolas; }
QLabel#stepTitle { color: #e8edf3; font-size: 12px; font-weight: 700; }
QLabel#stepCopy { color: #929eab; font-size: 10px; }
QLabel#dialogHint { color: #929eab; background-color: #10151b; padding: 9px; border-left: 2px solid #45c7d8; }
"""
