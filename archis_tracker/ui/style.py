"""
Archis Optical Tracker - Modern Stealth Aerospace Theme
Stylesheets and visual palette.
"""

DARK_THEME_QSS = """
QMainWindow, QDialog {
    background-color: #0c0d12;
    color: #e2e8f0;
    font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}

QWidget {
    background-color: #0c0d12;
    color: #e2e8f0;
    font-size: 12px;
}

/* Card panels */
QFrame#cardFrame {
    background-color: #141721;
    border: 1px solid #232838;
    border-radius: 12px;
}

QGroupBox {
    background-color: #141721;
    border: 1px solid #232838;
    border-radius: 10px;
    margin-top: 14px;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding-top: 16px;
    color: #94a3b8;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 6px;
    background-color: #141721;
    color: #ffffff;
}

/* Tab widget */
QTabWidget::pane {
    border: 1px solid #232838;
    background-color: #141721;
    border-radius: 10px;
    top: -1px;
}

QTabBar::tab {
    background-color: #0c0d12;
    color: #94a3b8;
    padding: 8px 16px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    border: 1px solid #232838;
    border-bottom: none;
    font-weight: 500;
    font-size: 11px;
}

QTabBar::tab:selected {
    background-color: #141721;
    color: #ffffff;
    font-weight: 600;
    border-bottom: 2px solid #38bdf8;
}

QTabBar::tab:hover:!selected {
    background-color: #1a1f2e;
    color: #cbd5e1;
}

/* Pushbuttons */
QPushButton {
    background-color: #1e2433;
    color: #f8fafc;
    border: 1px solid #2e374d;
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #2b3347;
    border-color: #3b82f6;
}

QPushButton:pressed {
    background-color: #181d29;
}

QPushButton#actionButton {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #ffffff;
    font-weight: 700;
}

QPushButton#actionButton:hover {
    background-color: #e2e8f0;
}

/* Sliders */
QSlider::groove:horizontal {
    border: 1px solid #232838;
    height: 6px;
    background: #1a1f2e;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #38bdf8;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 1px solid #94a3b8;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background: #38bdf8;
    border-color: #ffffff;
}

/* Combo boxes */
QComboBox {
    background-color: #1a1f2e;
    border: 1px solid #283045;
    border-radius: 7px;
    padding: 5px 12px;
    color: #ffffff;
    font-weight: 500;
}

QComboBox:hover {
    border-color: #38bdf8;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #141721;
    border: 1px solid #283045;
    selection-background-color: #283045;
    color: #ffffff;
    outline: none;
}

/* Checkboxes */
QCheckBox {
    spacing: 8px;
    color: #cbd5e1;
    font-weight: 500;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #334155;
    background-color: #1a1f2e;
}

QCheckBox::indicator:checked {
    background-color: #38bdf8;
    border-color: #38bdf8;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #0c0d12;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #283045;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
