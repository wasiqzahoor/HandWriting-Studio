"""Settings (spec 30): general, rendering, export, appearance, app."""
import os
import shutil
import subprocess
import sys as _sys

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QComboBox, QSpinBox, QSlider, QLineEdit,
                               QCheckBox, QFileDialog, QScrollArea, QGroupBox,
                               QFormLayout)
from PySide6.QtCore import Qt

from ui.components import (PageHeader, primary_button, ghost_button,
                           danger_button)


class SettingsPage(QWidget):
    def __init__(self, ctx, win):
        super().__init__()
        self.ctx = ctx
        self.win = win
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)
        root.addWidget(PageHeader("Settings",
                                  "Defaults, export, appearance and data."))
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        body = QWidget()
        body.setObjectName("scrollbody")
        lay = QVBoxLayout(body)
        lay.setSpacing(12)

        st = ctx.settings
        # general
        g = self._group(lay, "General")
        self.cmb_template = QComboBox()
        for t in ctx.templates.list():
            self.cmb_template.addItem(t.name, t.template_id)
        self._pick(self.cmb_template, st.get("default_template"))
        self.cmb_profile = QComboBox()
        for p in ctx.profiles.list_profiles():
            self.cmb_profile.addItem(p["meta"].get("name", p["id"]), p["id"])
        self._pick(self.cmb_profile, st.get("default_profile"))
        self.ed_export = QLineEdit(st.get("export_dir") or ctx.paths.exports)
        self.ed_export.setReadOnly(True)
        b_exp = ghost_button("Change...")
        b_exp.clicked.connect(self.pick_export)
        er = QHBoxLayout()
        er.addWidget(self.ed_export, 1)
        er.addWidget(b_exp)
        g.addRow("Default template:", self.cmb_template)
        g.addRow("Default handwriting profile:", self.cmb_profile)
        g.addRow("Default export location:", er)

        # rendering
        r = self._group(lay, "Rendering")
        self.spin_dpi = QSpinBox()
        self.spin_dpi.setRange(150, 600)
        self.spin_dpi.setValue(st.get("dpi", 300))
        self.sl_var = QSlider(Qt.Horizontal)
        self.sl_var.setRange(0, 100)
        self.sl_var.setValue(int(st.get("default_variation", 0.6) * 100))
        self.spin_size = QSpinBox()
        self.spin_size.setRange(20, 64)
        self.spin_size.setValue(st.get("default_font_size", 42))
        r.addRow("Default DPI:", self.spin_dpi)
        r.addRow("Default variation:", self.sl_var)
        r.addRow("Default font size:", self.spin_size)

        # export
        e = self._group(lay, "Export")
        self.ck_pdf = QCheckBox("PDF")
        self.ck_pdf.setChecked(bool(st.get("pdf_format", True)))
        self.ck_png = QCheckBox("PNG")
        self.ck_png.setChecked(bool(st.get("png_format", True)))
        self.ck_jpg = QCheckBox("JPEG")
        self.ck_jpg.setChecked(bool(st.get("jpg_format", False)))
        fr = QHBoxLayout()
        for c in (self.ck_pdf, self.ck_png, self.ck_jpg):
            fr.addWidget(c)
        fr.addStretch(1)
        self.ed_naming = QLineEdit(st.get("naming"))
        self.ed_naming.setPlaceholderText(
            "{template}_{profile}_{seed}_{date}")
        e.addRow("Formats:", fr)
        e.addRow("Naming:", self.ed_naming)

        # appearance
        a = self._group(lay, "Appearance")
        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems(["light", "dark"])
        self.cmb_theme.setCurrentText(st.get("theme", "light"))
        a.addRow("Theme:", self.cmb_theme)

        # application
        app = self._group(lay, "Application")
        info = QLabel(f"Handwriting Studio v1.0.0\nData: {ctx.paths.base}")
        info.setProperty("class", "muted")
        info.setWordWrap(True)
        info.setMinimumWidth(20)
        app.addRow(info)
        row = QHBoxLayout()
        b_logs = ghost_button("Open Logs Folder")
        b_logs.clicked.connect(lambda: self._open(ctx.paths.logs))
        b_data = ghost_button("Open Data Folder")
        b_data.clicked.connect(lambda: self._open(ctx.paths.base))
        b_reset = danger_button("Reset All Settings")
        b_reset.clicked.connect(self.reset)
        row.addWidget(b_logs)
        row.addWidget(b_data)
        row.addStretch(1)
        row.addWidget(b_reset)
        app.addRow(row)

        save = primary_button("Save Settings")
        save.clicked.connect(self.save)
        lay.addWidget(save)
        lay.addStretch(1)
        sc.setWidget(body)
        root.addWidget(sc, 1)

    def _group(self, parent, title):
        g = QGroupBox(title)
        g.setProperty("class", "card")
        f = QFormLayout(g)
        f.setSpacing(10)
        parent.addWidget(g)
        return f

    @staticmethod
    def _pick(combo, value):
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return

    def pick_export(self):
        d = QFileDialog.getExistingDirectory(self, "Default export location")
        if d:
            self.ed_export.setText(d)

    def _open(self, path):
        try:
            if _sys.platform == "win32":
                os.startfile(path)
            elif _sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            self.win.toast(f"Cannot open: {e}", "error")

    def save(self):
        st = self.ctx.settings
        st.set("default_template", self.cmb_template.currentData())
        st.set("default_profile", self.cmb_profile.currentData())
        st.set("export_dir", self.ed_export.text().strip())
        st.set("dpi", int(self.spin_dpi.value()))
        st.set("default_variation", self.sl_var.value() / 100.0)
        st.set("default_font_size", int(self.spin_size.value()))
        st.data["pdf_format"] = self.ck_pdf.isChecked()
        st.data["png_format"] = self.ck_png.isChecked()
        st.data["jpg_format"] = self.ck_jpg.isChecked()
        st.data["naming"] = self.ed_naming.text().strip() or \
            "{template}_{profile}_{seed}_{date}"
        theme = self.cmb_theme.currentText()
        st.set("theme", theme)
        st.save()
        self.win.apply_theme(theme)
        self.win.toast("Settings saved.")

    def reset(self):
        from PySide6.QtWidgets import QMessageBox
        if QMessageBox.question(
                self, "Reset settings",
                "Reset all settings to defaults?") == QMessageBox.Yes:
            self.ctx.settings.reset()
            self.win.apply_theme("light")
            self.win.toast("Settings reset to defaults.")

    def refresh(self):
        st = self.ctx.settings
        keep_t, keep_p = (self.cmb_template.currentData(),
                          self.cmb_profile.currentData())
        self.cmb_template.blockSignals(True)
        self.cmb_template.clear()
        for t in self.ctx.templates.list():
            self.cmb_template.addItem(t.name, t.template_id)
        self._pick(self.cmb_template, keep_t or st.get("default_template"))
        self.cmb_template.blockSignals(False)
        self.cmb_profile.blockSignals(True)
        self.cmb_profile.clear()
        for p in self.ctx.profiles.list_profiles():
            self.cmb_profile.addItem(p["meta"].get("name", p["id"]), p["id"])
        self._pick(self.cmb_profile, keep_p or st.get("default_profile"))
        self.cmb_profile.blockSignals(False)
        self.ed_export.setText(st.get("export_dir") or self.ctx.paths.exports)
        self.spin_dpi.setValue(st.get("dpi", 300))
        self.sl_var.setValue(int(st.get("default_variation", 0.6) * 100))
        self.spin_size.setValue(st.get("default_font_size", 42))
        self.ck_pdf.setChecked(bool(st.get("pdf_format", True)))
        self.ck_png.setChecked(bool(st.get("png_format", True)))
        self.ck_jpg.setChecked(bool(st.data.get("jpg_format", False)))
        self.ed_naming.setText(st.get("naming"))
        self.cmb_theme.setCurrentText(st.get("theme", "light"))
