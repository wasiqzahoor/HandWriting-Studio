"""Profiles page (spec 22-23): cards, validation, import/export, delete."""
import os

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QScrollArea, QDialog, QFormLayout, QFileDialog,
                               QMessageBox, QTableWidgetItem)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PIL import Image
from PIL.ImageQt import ImageQt

from ui.components import (PageHeader, Card, primary_button, ghost_button,
                           danger_button, make_table, set_table_rows)
from handwriting_engine.profile import coverage_report


def preview_strip(ctx, profile_id, w=320):
    try:
        img, _w, _i = ctx.documents.render(
            "four_by_six", {"header": "", "body": "Aa Bb Cc Dd Ee 123"},
            profile_id, {"font_size": 40, "seed": 5, "variation": 0.4})
        crop = img.crop((90, 700, 1110, 1050))
        crop.thumbnail((w, 200))
        if crop.mode == "RGBA":
            bg = Image.new("RGB", crop.size, (255, 255, 255))
            bg.paste(crop, mask=crop.split()[-1])
            crop = bg
        return QPixmap.fromImage(ImageQt(crop))
    except Exception:
        return None


class ProfileViewDialog(QDialog):
    def __init__(self, parent, ctx, profile_id):
        super().__init__(parent)
        prof = ctx.profiles.get(profile_id, fresh=True)
        meta = prof["meta"]
        self.setWindowTitle(meta.get("name", profile_id))
        self.setMinimumSize(460, 420)
        lay = QVBoxLayout(self)
        info = QLabel(f"<b>{meta.get('name')}</b> v{meta.get('version')} "
                      f"\u00b7 by {meta.get('author', '-')}<br>"
                      f"Renderer: {meta.get('renderer')}<br>"
                      f"{meta.get('description', '')}<br>"
                      f"Glyphs: {len(prof['supported'])} supported characters")
        info.setWordWrap(True)
        lay.addWidget(info)
        lay.addWidget(QLabel("<b>Character coverage</b>"))
        tbl = make_table(["Group", "Have", "Total", "Missing"])
        rep = coverage_report(prof)
        set_table_rows(tbl, [(g, v["have"], v["total"],
                              "".join(v["missing"])[:24]) for g, v in
                             rep.items()])
        lay.addWidget(tbl)
        warns = ctx.profiles.validate(profile_id)
        lay.addWidget(QLabel("<b>Validation</b>"))
        wlab = QLabel("\n".join(f"\u26a0 {w}" for w in warns)
                      if warns else "\u2713 Profile is healthy.")
        wlab.setWordWrap(True)
        lay.addWidget(wlab)


class ProfilesPage(QWidget):
    def __init__(self, ctx, win):
        super().__init__()
        self.ctx = ctx
        self.win = win
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)
        head = PageHeader("Handwriting Profiles",
                          "Each profile is independent data - add new styles "
                          "without changing the app.")
        imp = ghost_button("Import Profile (.hwprofile)")
        imp.clicked.connect(self.do_import)
        new = primary_button("+ Create via Training")
        new.clicked.connect(lambda: win.goto(4))
        head.add_action(imp)
        head.add_action(new)
        root.addWidget(head)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        self.wrap = QWidget()
        self.wrap.setObjectName("scrollbody")
        self.list = QVBoxLayout(self.wrap)
        self.list.setSpacing(12)
        sc.setWidget(self.wrap)
        root.addWidget(sc, 1)
        self.refresh()

    def refresh(self):
        while self.list.count():
            item = self.list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        dflt = self.ctx.settings.get("default_profile")
        for prof in self.ctx.profiles.list_profiles():
            self.list.addWidget(self._card(prof, prof["id"] == dflt))
        self.list.addStretch(1)

    def _card(self, prof, is_default):
        pid = prof["id"]
        meta = prof["meta"]
        is_user = os.path.abspath(prof.get("dir", "")).startswith(
            os.path.abspath(self.ctx.paths.profiles))
        c = Card()
        top = QHBoxLayout()
        title = QLabel(f"{meta.get('name', pid)}  v{meta.get('version', '?')}"
                       f"{'  \u00b7  DEFAULT' if is_default else ''}"
                       f"{'' if is_user else '  \u00b7  BUNDLED'}")
        title.setStyleSheet("font-weight: 800; font-size: 15px;")
        top.addWidget(title, 1)
        badge = QLabel(meta.get("renderer", "glyph_based"))
        badge.setProperty("class", "sizebadge")
        top.addWidget(badge)
        c.layout().addLayout(top)
        sub = QLabel(f"by {meta.get('author', '-')}  \u00b7  "
                     f"{len(prof['supported'])} glyphs  \u00b7  "
                     f"{meta.get('description', '')}")
        sub.setProperty("class", "muted")
        sub.setWordWrap(True)
        c.layout().addWidget(sub)
        pm = preview_strip(self.ctx, pid)
        if pm is not None:
            lab = QLabel()
            lab.setAlignment(Qt.AlignCenter)
            lab.setPixmap(pm)
            c.layout().addWidget(lab)
        warns = self.ctx.profiles.validate(pid)
        if warns:
            w = QLabel("\u26a0 " + warns[0])
            w.setStyleSheet("color: #B7791F; font-size: 12px;")
            w.setWordWrap(True)
            c.layout().addWidget(w)
        row = QHBoxLayout()
        row.setSpacing(8)
        use = primary_button("Use")
        use.clicked.connect(lambda _=False, i=pid: self._use(i))
        view = ghost_button("View")
        view.clicked.connect(lambda _=False, i=pid: self._view(i))
        exp = ghost_button("Export")
        exp.clicked.connect(lambda _=False, i=pid: self._export(i))
        row.addWidget(use)
        row.addWidget(view)
        row.addWidget(exp)
        if is_user:
            dele = danger_button("Delete")
            dele.clicked.connect(lambda _=False, i=pid: self._delete(i))
            row.addWidget(dele)
        row.addStretch(1)
        c.layout().addLayout(row)
        return c

    def _use(self, pid):
        self.ctx.settings.set("default_profile", pid)
        self.refresh()
        self.win.toast(f"Default profile: {pid}")

    def _view(self, pid):
        ProfileViewDialog(self, self.ctx, pid).exec()

    def _export(self, pid):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export profile", f"{pid}.hwprofile",
            "Handwriting profile (*.hwprofile)")
        if path:
            try:
                self.ctx.profiles.export_zip(pid, path)
                self.win.toast(f"Profile exported: {path}")
            except Exception as e:
                self.win.toast(str(e), "error")

    def do_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import profile", "", "Handwriting profile (*.hwprofile *.zip)")
        if not path:
            return
        try:
            pid, warnings = self.ctx.profiles.import_zip(path)
            self.refresh()
            self.win.toast(f"Profile imported: {pid}")
            for w in warnings:
                self.win.toast(w, "warn")
        except Exception as e:
            QMessageBox.warning(self, "Import failed", str(e))

    def _delete(self, pid):
        if QMessageBox.question(
                self, "Delete profile",
                f"Delete profile '{pid}'?") != QMessageBox.Yes:
            return
        try:
            self.ctx.profiles.delete(pid)
            self.refresh()
            self.win.toast("Profile deleted.")
        except Exception as e:
            self.win.toast(str(e), "error")
