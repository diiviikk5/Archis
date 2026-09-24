"""
Archis Desktop Design System - Windows 11 Fluent Design & Aerospace Theme.
"""
from PyQt6.QtGui import QColor
from qfluentwidgets import setTheme, Theme, setThemeColor


def init_fluent_theme():
    """Initializes Microsoft Fluent dark theme and titanium cyan accent color."""
    setTheme(Theme.DARK)
    setThemeColor(QColor("#00A4EF"))


DARK_THEME_QSS = """
QMainWindow, QDialog {
    background-color: #0b0f14;
    color: #f0f6fc;
}

QSplitter::handle {
    background-color: #1f2937;
    width: 2px;
}

QSplitter::handle:hover {
    background-color: #00a4ef;
}

/* App Header */
QFrame#appHeader {
    min-height: 58px;
    max-height: 58px;
    background-color: #0e131a;
    border-bottom: 1px solid #1f2937;
}

QLabel#brandMark {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0078d4, stop:1 #00b4d8);
    color: #ffffff;
    border-radius: 8px;
    font-size: 18px;
    font-weight: 800;
}

QLabel#brandTitle {
    font-size: 17px;
    font-weight: 800;
    letter-spacing: 2px;
    color: #f0f6fc;
}

QLabel#brandSubtitle {
    color: #8b949e;
    font-size: 9px;
    letter-spacing: 1.5px;
    font-weight: 600;
}

QLabel#terminalLabel {
    color: #8b949e;
    font: 11px "Segoe UI Semibold", "Segoe UI";
    padding-left: 4px;
}

QLabel#engineBadge {
    color: #34d399;
    background-color: #062319;
    border: 1px solid #059669;
    border-radius: 6px;
    padding: 5px 10px;
    font: 700 10px Consolas, monospace;
}

QFrame#headerDivider {
    color: #1f2937;
    width: 1px;
}

/* Workspaces & Sidebar */
QWidget#navigationRail {
    background-color: #0e131a;
    border-right: 1px solid #1f2937;
}

QLabel#railBrand {
    font-size: 20px;
    font-weight: 800;
    letter-spacing: 1.5px;
    color: #f0f6fc;
    background: transparent;
}

QLabel#pageTitle {
    font-size: 26px;
    font-weight: 700;
    color: #f0f6fc;
    background: transparent;
}

QLabel#pageSubtitle {
    font-size: 13px;
    color: #8b949e;
    background: transparent;
    line-height: 1.4;
}

QLabel#sectionTitle {
    font-size: 16px;
    font-weight: 600;
    color: #f0f6fc;
    background: transparent;
}

QWidget#homeAction {
    background-color: #131922;
    border: 1px solid #1f2937;
    border-radius: 10px;
    padding: 16px 20px;
}

QWidget#homeAction:hover {
    border-color: #00a4ef;
    background-color: #17202b;
}

/* Card Frames */
QFrame#cardFrame {
    background-color: #131922;
    border: 1px solid #1f2937;
    border-radius: 8px;
}

QFrame#cardFrame:hover {
    border-color: #2e3c4e;
}

/* Scrollbars */
QScrollBar:vertical {
    width: 8px;
    background: transparent;
    margin: 0;
}

QScrollBar::handle:vertical {
    min-height: 28px;
    background: #2d3748;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #4a5568;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    height: 8px;
    background: transparent;
}

QScrollBar::handle:horizontal {
    min-width: 28px;
    background: #2d3748;
    border-radius: 4px;
}

/* Status Bar */
QStatusBar {
    min-height: 28px;
    max-height: 28px;
    background-color: #0e131a;
    color: #8b949e;
    border-top: 1px solid #1f2937;
    font-size: 11px;
}

QStatusBar::item {
    border: none;
}

/* Review Document */
QFrame#reviewEmptyState {
    border: 1px solid #1f2937;
    border-radius: 8px;
    background-color: #131922;
}
QFrame#reviewEmptyState QLabel {
    color: #aab6c5;
    font-size: 14px;
}
QTextBrowser#reviewDocument {
    border: 1px solid #1f2937;
    border-radius: 8px;
    background-color: #131922;
    color: #e6edf3;
    padding: 24px;
    font-size: 13px;
    font-family: "Segoe UI", sans-serif;
}
"""
