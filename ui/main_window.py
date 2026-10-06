"""Main window: persistent black sidebar + stacked pages (spec 15)."""
import os

from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                               QLabel, QPushButton, QStackedWidget, QFrame,
                               QButtonGroup)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QShortcut, QKeySequence

from ui.styles import THEMES
from ui.components import Toast
from ui.icons import icon as nav_icon

NAV = [("Dashboard", "dashboard"), ("Document Creator", "creator"),
       ("Templates", "templates"), ("Profiles", "profiles"),
       ("Training", "training"), ("Batch Jobs", "batch"),
       ("Exports", "exports"), ("Settings", "settings")]


class Sidebar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(228)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 18, 14, 14)
        lay.setSpacing(4)
        brand = QHBoxLayout()
        brand.setSpacing(10)
        logo = QLabel()
        icon_p = os.path.join(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))), "assets", "icon.png")
        if os.path.isfile(icon_p):
            logo.setPixmap(QPixmap(icon_p).scaled(
                34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            logo.setText("\u25c9")
            logo.setStyleSheet("color: #E63946; font-size: 24px;")
        brand.addWidget(logo)
        bt = QVBoxLayout()
        bt.setSpacing(0)
        b1 = QLabel("Handwriting Studio")
        b1.setProperty("class", "sidebrand")
        b2 = QLabel("Desktop Edition")
        b2.setProperty("class", "sidesub")
        bt.addWidget(b1)
        bt.addWidget(b2)
        brand.addLayout(bt, 1)
        lay.addLayout(brand)
        lay.addSpacing(14)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons = []
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QIcon
        for i, (name, icon_key) in enumerate(NAV):
            b = QPushButton(f"  {name}")
            b.setObjectName("nav")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setIcon(QIcon(nav_icon(icon_key)))
            b.setIconSize(QSize(19, 19))
            self.group.addButton(b, i)
            lay.addWidget(b)
            self.buttons.append(b)
        lay.addStretch(1)
        ver = QLabel("v1.0.0  \u00b7  offline")
        ver.setProperty("class", "sidever")
        lay.addWidget(ver)
        self.buttons[0].setChecked(True)


class MainWindow(QMainWindow):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle("Handwriting Studio")
        self.resize(1280, 820)
        self.setMinimumSize(1024, 680)
        icon_p = os.path.join(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))), "assets", "icon.png")
        if os.path.isfile(icon_p):
            from PySide6.QtGui import QIcon
            self.setWindowIcon(QIcon(icon_p))

        central = QWidget()
        self.setCentralWidget(central)
        lay = QHBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.sidebar = Sidebar()
        lay.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)

        # pages (lazy imports keep startup snappy)
        from ui.pages.dashboard import DashboardPage
        from ui.pages.document_creator import DocumentCreatorPage
        from ui.pages.templates import TemplatesPage
        from ui.pages.profiles import ProfilesPage
        from ui.pages.training import TrainingPage
        from ui.pages.batch import BatchPage
        from ui.pages.exports import ExportsPage
        from ui.pages.settings import SettingsPage
        self.pages = [DashboardPage(ctx, self), DocumentCreatorPage(ctx, self),
                      TemplatesPage(ctx, self), ProfilesPage(ctx, self),
                      TrainingPage(ctx, self), BatchPage(ctx, self),
                      ExportsPage(ctx, self), SettingsPage(ctx, self)]
        for p in self.pages:
            p.setObjectName("page")
            self.stack.addWidget(p)
        self.sidebar.group.idClicked.connect(self.goto)
        for i in range(len(NAV)):
            sc = QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self)
            sc.setContext(Qt.ApplicationShortcut)
            sc.activated.connect(lambda i=i: self._goto_shortcut(i))
        self.statusBar().showMessage("Ready.")
        self.apply_theme(ctx.settings.get("theme", "light"))

    def _goto_shortcut(self, index):
        self.sidebar.buttons[index].setChecked(True)
        self.goto(index)

    def apply_theme(self, name):
        from PySide6.QtWidgets import QApplication
        QApplication.instance().setStyleSheet(
            THEMES.get(name, THEMES["light"]))

    def goto(self, index):
        self.stack.setCurrentIndex(index)
        page = self.pages[index]
        if hasattr(page, "refresh"):
            try:
                page.refresh()
            except Exception as e:
                self.ctx.log.error("page refresh failed: %s", e)
        self.statusBar().showMessage(NAV[index][0])

    def toast(self, message, kind="ok"):
        Toast.notify(self, message, kind)
