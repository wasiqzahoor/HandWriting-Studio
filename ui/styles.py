"""Brand themes (spec 13, 48). Light default; dark optional.

Light: white surfaces, black sidebar, red CTA, sea-green success.
Dark:  black surfaces, red CTA, sea-green success.
"""
RED = "#E63946"
RED_HOVER = "#F2545B"
RED_PRESS = "#BE123C"
GREEN = "#2A9D8F"
GREEN_HOVER = "#33B5A4"
YELLOW = "#B7791F"

LIGHT = """
* { font-family: 'Segoe UI', 'SF Pro Text', Helvetica, Arial, sans-serif; }
QMainWindow { background: #F4F4F5; }
QWidget#page { background: #F4F4F5; }
QLabel { color: #111113; background: transparent; }
QLabel.muted { color: #6B7280; }
QLabel.hint { color: #9CA3AF; font-size: 11px; }
QLabel.pagetitle { font-size: 22px; font-weight: 800; color: #111113; }
QLabel.pagesub { font-size: 13px; color: #6B7280; }
QLabel.badge { background: #E63946; color: white; font-weight: 800;
    font-size: 11px; border-radius: 6px; padding: 4px 10px; }
QLabel.sizebadge { background: #EDEDEF; color: #6B7280; font-size: 11px;
    border: 1px solid #E4E4E7; border-radius: 6px; padding: 4px 10px; }
QLabel.statvalue { font-size: 22px; font-weight: 800; color: #111113; }
QLabel.statlabel { font-size: 12px; color: #6B7280; }
QFrame#sidebar { background: #0B0B0D; border: none; }
QLabel.sidebrand { color: white; font-size: 15px; font-weight: 800; }
QLabel.sidesub { color: #A1A1AA; font-size: 11px; }
QLabel.sidever { color: #52525B; font-size: 11px; }
QPushButton#nav { background: transparent; color: #D4D4D8; border: none;
    border-radius: 8px; padding: 10px 12px; font-size: 13px; font-weight: 600;
    text-align: left; }
QPushButton#nav:hover { background: #1A1A1E; color: white; }
QPushButton#nav:checked { background: #1E1E23; color: white;
    border-left: 3px solid #E63946; border-radius: 0px;
    border-top-right-radius: 8px; border-bottom-right-radius: 8px; }
QGroupBox.card, QFrame.card { background: white; border: 1px solid #E4E4E7;
    border-radius: 12px; }
QGroupBox.card { margin-top: 14px; padding: 12px; font-weight: 700;
    font-size: 12px; letter-spacing: 1px; color: #111113; }
QGroupBox.card::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
QTextEdit, QLineEdit, QSpinBox, QComboBox, QDateEdit { background: white;
    border: 1px solid #D4D4D8; border-radius: 8px; padding: 8px; color: #111113;
    selection-background-color: #E63946; }
QTextEdit:focus, QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #E63946; }
QComboBox::drop-down { border: none; width: 26px; }
QPushButton { border-radius: 8px; padding: 9px 14px; font-weight: 700;
    font-size: 13px; }
QPushButton#btnPrimary { background: #E63946; color: white; }
QPushButton#btnPrimary:hover { background: #F2545B; }
QPushButton#btnPrimary:pressed { background: #BE123C; }
QPushButton#btnPrimary:disabled { background: #E4E4E7; color: #9CA3AF; }
QPushButton#btnExport { background: #2A9D8F; color: white; }
QPushButton#btnExport:hover { background: #33B5A4; }
QPushButton#btnExport:disabled { background: #E4E4E7; color: #9CA3AF; }
QPushButton#btnGhost { background: white; color: #111113;
    border: 1px solid #D4D4D8; }
QPushButton#btnGhost:hover { border: 1px solid #E63946; color: #E63946; }
QPushButton#btnDanger { background: transparent; color: #E63946;
    border: 1px solid #FECDD3; }
QPushButton#btnDanger:hover { background: #FFF1F2; }
QSlider::groove:horizontal { height: 6px; background: #E4E4E7;
    border-radius: 3px; }
QSlider::sub-page:horizontal { background: #E63946; border-radius: 3px; }
QSlider::handle:horizontal { width: 16px; margin: -6px 0; border-radius: 8px;
    background: #E63946; border: 2px solid white; }
QProgressBar { background: #EDEDEF; border: none; border-radius: 6px;
    height: 12px; text-align: center; color: #6B7280; font-size: 10px; }
QProgressBar::chunk { background: #E63946; border-radius: 6px; }
QTableWidget { background: white; border: 1px solid #E4E4E7; border-radius: 8px;
    gridline-color: #F0F0F2; color: #111113; }
QTableWidget::item { padding: 4px; }
QHeaderView::section { background: #F7F7F8; color: #6B7280; border: none;
    padding: 8px; font-weight: 700; }
QScrollArea { border: none; background: #F4F4F5; }
QScrollArea > QWidget { background: #F4F4F5; }
QWidget#scrollbody { background: #F4F4F5; }
QLabel#docframe { background: white; border: 1px solid #E4E4E7;
    border-radius: 10px; color: #6B7280; font-size: 13px; }
QLabel#samplebox { background: #F7F7F8; border: 1px dashed #D4D4D8;
    border-radius: 8px; color: #6B7280; }
QSplitter::handle { background: #F4F4F5; }
QSplitter::handle:horizontal { width: 2px; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #D4D4D8; border-radius: 5px;
    min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #D4D4D8; border-radius: 5px;
    min-width: 30px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QStatusBar { background: white; color: #6B7280;
    border-top: 1px solid #E4E4E7; }
QCheckBox { color: #111113; spacing: 8px; }
QToolTip { background: #111113; color: white; border: none; padding: 6px; }
"""

DARK = """
* { font-family: 'Segoe UI', 'SF Pro Text', Helvetica, Arial, sans-serif; }
QMainWindow { background: #0B0B0D; }
QWidget#page { background: #0B0B0D; }
QLabel { color: #F5F5F7; background: transparent; }
QLabel.muted { color: #A1A1AA; }
QLabel.hint { color: #71717A; font-size: 11px; }
QLabel.pagetitle { font-size: 22px; font-weight: 800; color: white; }
QLabel.pagesub { font-size: 13px; color: #A1A1AA; }
QLabel.badge { background: #E63946; color: white; font-weight: 800;
    font-size: 11px; border-radius: 6px; padding: 4px 10px; }
QLabel.sizebadge { background: #1D1D21; color: #A1A1AA; font-size: 11px;
    border: 1px solid #26262C; border-radius: 6px; padding: 4px 10px; }
QLabel.statvalue { font-size: 22px; font-weight: 800; color: white; }
QLabel.statlabel { font-size: 12px; color: #A1A1AA; }
QFrame#sidebar { background: #000000; border: none;
    border-right: 1px solid #1C1C20; }
QLabel.sidebrand { color: white; font-size: 15px; font-weight: 800; }
QLabel.sidesub { color: #A1A1AA; font-size: 11px; }
QLabel.sidever { color: #52525B; font-size: 11px; }
QPushButton#nav { background: transparent; color: #D4D4D8; border: none;
    border-radius: 8px; padding: 10px 12px; font-size: 13px; font-weight: 600;
    text-align: left; }
QPushButton#nav:hover { background: #1A1A1E; color: white; }
QPushButton#nav:checked { background: #1E1E23; color: white;
    border-left: 3px solid #E63946; border-radius: 0px;
    border-top-right-radius: 8px; border-bottom-right-radius: 8px; }
QGroupBox.card, QFrame.card { background: #141417; border: 1px solid #26262C;
    border-radius: 12px; }
QGroupBox.card { margin-top: 14px; padding: 12px; font-weight: 700;
    font-size: 12px; letter-spacing: 1px; color: white; }
QGroupBox.card::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
QTextEdit, QLineEdit, QSpinBox, QComboBox { background: #0E0E11;
    border: 1px solid #2C2C31; border-radius: 8px; padding: 8px; color: white;
    selection-background-color: #E63946; }
QTextEdit:focus, QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #E63946; }
QComboBox::drop-down { border: none; width: 26px; }
QPushButton { border-radius: 8px; padding: 9px 14px; font-weight: 700;
    font-size: 13px; }
QPushButton#btnPrimary { background: #E63946; color: white; }
QPushButton#btnPrimary:hover { background: #F2545B; }
QPushButton#btnPrimary:pressed { background: #BE123C; }
QPushButton#btnPrimary:disabled { background: #2A2A30; color: #71717A; }
QPushButton#btnExport { background: #2A9D8F; color: white; }
QPushButton#btnExport:hover { background: #33B5A4; }
QPushButton#btnExport:disabled { background: #2A2A30; color: #71717A; }
QPushButton#btnGhost { background: transparent; color: #F5F5F7;
    border: 1px solid #3A3A41; }
QPushButton#btnGhost:hover { border: 1px solid #E63946; color: white; }
QPushButton#btnDanger { background: transparent; color: #F2545B;
    border: 1px solid #5B2329; }
QPushButton#btnDanger:hover { background: #2A1518; }
QSlider::groove:horizontal { height: 6px; background: #232329;
    border-radius: 3px; }
QSlider::sub-page:horizontal { background: #E63946; border-radius: 3px; }
QSlider::handle:horizontal { width: 16px; margin: -6px 0; border-radius: 8px;
    background: #E63946; border: 2px solid #0B0B0D; }
QProgressBar { background: #1D1D21; border: none; border-radius: 6px;
    height: 12px; text-align: center; color: #A1A1AA; font-size: 10px; }
QProgressBar::chunk { background: #E63946; border-radius: 6px; }
QTableWidget { background: #141417; border: 1px solid #26262C;
    border-radius: 8px; gridline-color: #1E1E23; color: #F5F5F7; }
QTableWidget::item { padding: 4px; }
QHeaderView::section { background: #1A1A1E; color: #A1A1AA; border: none;
    padding: 8px; font-weight: 700; }
QScrollArea { border: none; background: #0B0B0D; }
QScrollArea > QWidget { background: #0B0B0D; }
QWidget#scrollbody { background: #0B0B0D; }
QLabel#docframe { background: #1A1A1F; border: 1px solid #26262C;
    border-radius: 10px; color: #A1A1AA; font-size: 13px; }
QLabel#samplebox { background: #0E0E11; border: 1px dashed #3A3A41;
    border-radius: 8px; color: #A1A1AA; }
QSplitter::handle { background: #0B0B0D; }
QSplitter::handle:horizontal { width: 2px; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #2E2E35; border-radius: 5px;
    min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #2E2E35; border-radius: 5px;
    min-width: 30px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QStatusBar { background: #101013; color: #A1A1AA;
    border-top: 1px solid #26262C; }
QCheckBox { color: #F5F5F7; spacing: 8px; }
QToolTip { background: #1A1A1E; color: white; border: 1px solid #2C2C31;
    padding: 6px; }
"""

# Shared finishing rules appended to both themes: dialogs, combo popups,
# list widgets, table selection, consistent control heights.
SHARED = """
QPushButton#nav { min-height: 22px; }
QDialog { background: palette(window); }
QDialogButtonBox QPushButton {
    background: transparent; border: 1px solid #888893;
    border-radius: 8px; padding: 8px 16px; font-weight: 700; }
QComboBox QAbstractItemView {
    border: 1px solid #888893; border-radius: 0px;
    selection-background-color: #E63946; selection-color: white;
    outline: none; padding: 4px; }
QListWidget { border: 1px solid #888893; border-radius: 8px; padding: 4px; }
QListWidget::item { padding: 5px; border-radius: 4px; }
QListWidget::item:selected { background: #E63946; color: white; }
QTableWidget { selection-background-color: rgba(230, 57, 70, 28); }
QTableWidget::item:selected { color: palette(text); }
QGroupBox::indicator { width: 15px; height: 15px; }
QSpinBox { min-height: 22px; }
QLineEdit, QComboBox { min-height: 20px; }
QTextEdit { min-height: 60px; }
"""

THEMES = {"light": LIGHT + SHARED, "dark": DARK + SHARED}
