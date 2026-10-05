"""AppContext: wires all engines together (spec 4 - application layer)."""
from core.configuration import AppSettings
from core.logging import get_logger
from storage.database import Database
from handwriting_engine.profile_manager import ProfileManager
from handwriting_engine.engine import HandwritingEngine
from template_engine.manager import TemplateManager
from document_engine.document import DocumentService
from export_engine.export_manager import ExportManager

log = get_logger("studio")


class AppContext:
    def __init__(self, paths, bundled_profiles_dir):
        self.paths = paths.ensure()
        self.settings = AppSettings(paths.settings_file)
        self.db = Database(paths.db_file)
        self.profiles = ProfileManager(paths.profiles, bundled_profiles_dir)
        self.hw = HandwritingEngine(self.profiles)
        self.templates = TemplateManager(paths.templates)
        self.documents = DocumentService(self.hw, self.templates)
        self.exports = ExportManager(self.db, paths.exports)
        self.log = log

    def default_profile_id(self):
        want = self.settings.get("default_profile")
        ids = self.profiles.list_ids()
        if want in ids:
            return want
        self.settings.set("default_profile", ids[0] if ids else "")
        return self.settings.get("default_profile")

    def shutdown(self):
        pass
