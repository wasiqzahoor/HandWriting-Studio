"""Reusable UI components (spec 46). Every page shares these."""
from PySide6.QtWidgets import (QFrame, QLabel, QPushButton, QVBoxLayout,
                               QHBoxLayout, QWidget, QTableWidget,
                               QTableWidgetItem, QHeaderView, QAbstractItemView,
                               QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, QTimer, Signal


def primary_button(text):
    b = QPushButton(text)
    b.setObjectName("btnPrimary")
    return b


def export_button(text):
    b = QPushButton(text)
    b.setObjectName("btnExport")
    return b


def ghost_button(text):
    b = QPushButton(text)
    b.setObjectName("btnGhost")
    return b


def danger_button(text):
    b = QPushButton(text)
    b.setObjectName("btnDanger")
    return b


class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(16, 16, 16, 16)
        self.layout().setSpacing(10)


class PageHeader(QWidget):
    def __init__(self, title, subtitle="", parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        left = QVBoxLayout()
        left.setSpacing(2)
        t = QLabel(title)
        t.setProperty("class", "pagetitle")
        s = QLabel(subtitle)
        s.setProperty("class", "pagesub")
        s.setWordWrap(True)
        left.addWidget(t)
        left.addWidget(s)
        lay.addLayout(left, 1)
        self.actions = QHBoxLayout()
        self.actions.setSpacing(8)
        lay.addLayout(self.actions)

    def add_action(self, widget):
        self.actions.addWidget(widget)


class StatCard(Card):
    def __init__(self, label, value="0", parent=None):
        super().__init__(parent)
        self.layout().setContentsMargins(12, 10, 12, 10)
        self.layout().setSpacing(2)
        self.v = QLabel(str(value))
        self.v.setProperty("class", "statvalue")
        self.v.setAlignment(Qt.AlignCenter)
        l = QLabel(label)
        l.setProperty("class", "statlabel")
        l.setAlignment(Qt.AlignCenter)
        self.layout().addWidget(self.v)
        self.layout().addWidget(l)

    def set_value(self, v):
        self.v.setText(str(v))


class EmptyState(QWidget):
    def __init__(self, title, subtitle="", action_text="", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(6)
        lay.setContentsMargins(10, 18, 10, 18)
        icon = QLabel("\u25cb")
        icon.setStyleSheet("font-size: 32px; color: #9CA3AF;")
        icon.setAlignment(Qt.AlignCenter)
        t = QLabel(title)
        t.setStyleSheet("font-size: 15px; font-weight: 700;")
        t.setAlignment(Qt.AlignCenter)
        s = QLabel(subtitle)
        s.setProperty("class", "muted")
        s.setWordWrap(True)
        s.setAlignment(Qt.AlignCenter)
        lay.addWidget(icon)
        lay.addWidget(t)
        lay.addWidget(s)
        self.button = None
        if action_text:
            self.button = primary_button(action_text)
            row = QHBoxLayout()
            row.addStretch(1)
            row.addWidget(self.button)
            row.addStretch(1)
            lay.addLayout(row)


class Toast(QLabel):
    _current = None

    def __init__(self, parent, message, kind="ok"):
        colors = {"ok": ("#2A9D8F", "white"), "warn": ("#B7791F", "white"),
                  "error": ("#E63946", "white"), "info": ("#111113", "white")}
        bg, fg = colors.get(kind, colors["ok"])
        super().__init__(f"{message}", parent)
        self.setStyleSheet(f"background: {bg}; color: {fg}; font-weight: 700;"
                           "font-size: 13px; border-radius: 10px; padding: 12px 18px;")
        eff = QGraphicsDropShadowEffect(self)
        eff.setBlurRadius(24)
        eff.setOffset(0, 6)
        self.setGraphicsEffect(eff)
        self.adjustSize()
        pw = parent.width()
        self.move(max(10, pw - self.width() - 24),
                  max(10, parent.height() - self.height() - 48))
        self.show()
        self.raise_()
        QTimer.singleShot(3400, self._fade)

    def _fade(self):
        self.hide()
        self.deleteLater()

    @staticmethod
    def notify(parent, message, kind="ok"):
        try:
            if Toast._current is not None:
                Toast._current.hide()
        except Exception:
            pass
        # find top-level content widget for stable placement
        host = parent.window() if hasattr(parent, "window") else parent
        Toast._current = Toast(host, message, kind)


def make_table(columns):
    t = QTableWidget()
    t.setColumnCount(len(columns))
    t.setHorizontalHeaderLabels(columns)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    t.verticalHeader().setVisible(False)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.SingleSelection)
    return t


def set_table_rows(table, rows):
    table.setRowCount(len(rows))
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            table.setItem(i, j, QTableWidgetItem(str(val)))
