"""Platform-appropriate application directories (spec section 38).

Layout (no hard-coded user paths):
    <base>/
        profiles/    handwriting profiles (bundled + user)
        templates/   template JSON files
        exports/     default export output
        logs/        application logs
        cache/       thumbnails / temp files

Base is QStandardPaths.AppDataLocation when available
(~/Library/Application Support/<App> on macOS,
 %APPDATA%/<App> on Windows); falls back to <project>/.data for dev runs.
"""
import os

APP_NAME = "HandwritingStudio"
APP_ORG = "HandwritingStudio"


def _qt_appdata():
    try:
        from PySide6.QtCore import QStandardPaths
        p = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        if p:
            return p
    except Exception:
        pass
    return ""


class PlatformPaths:
    def __init__(self, base=None, portable=False):
        if base:
            self.base = base
        elif portable or not _qt_appdata():
            here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.base = os.path.join(here, ".data")
        else:
            self.base = _qt_appdata()
        self.profiles = os.path.join(self.base, "profiles")
        self.templates = os.path.join(self.base, "templates")
        self.exports = os.path.join(self.base, "exports")
        self.logs = os.path.join(self.base, "logs")
        self.cache = os.path.join(self.base, "cache")
        self.db_file = os.path.join(self.base, "studio.db")
        self.settings_file = os.path.join(self.base, "settings.json")

    def ensure(self):
        for d in (self.base, self.profiles, self.templates,
                  self.exports, self.logs, self.cache):
            os.makedirs(d, exist_ok=True)
        return self

    def as_dict(self):
        return {"base": self.base, "profiles": self.profiles,
                "templates": self.templates, "exports": self.exports,
                "logs": self.logs, "cache": self.cache}
