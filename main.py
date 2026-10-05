"""Handwriting Studio - production desktop app entry point.

Usage:
    python main.py [--portable]
    python3 main.py [--portable]      (macOS / Linux)

--portable keeps all app data inside ./.data (dev/testing). Default uses
OS-appropriate directories (~/Library/Application Support/... on macOS,
%APPDATA% on Windows).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from core.paths import PlatformPaths
from core.logging import setup_logging
from core.application import AppContext
from ui.main_window import MainWindow

VERSION = "1.0.0"


def main():
    portable = "--portable" in sys.argv
    base_dir = os.path.dirname(os.path.abspath(__file__))
    paths = PlatformPaths(base=None, portable=portable)
    paths.ensure()
    setup_logging(paths.logs)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # identical theme on Windows + macOS
    app.setApplicationName("Handwriting Studio")
    app.setOrganizationName("HandwritingStudio")
    app.setApplicationVersion(VERSION)
    icon = os.path.join(base_dir, "assets", "icon.png")
    if os.path.isfile(icon):
        app.setWindowIcon(QIcon(icon))
    bundled = os.path.join(base_dir, "handwriting_engine", "profiles")
    ctx = AppContext(paths, bundled)
    ctx.log.info("Handwriting Studio v%s starting (portable=%s)",
                 VERSION, portable)
    ctx.log.info("profiles=%d templates=%d", len(ctx.profiles.list_ids()),
                 len(ctx.templates.list()))
    win = MainWindow(ctx)
    win.show()
    code = app.exec()
    ctx.shutdown()
    sys.exit(code)


if __name__ == "__main__":
    main()
