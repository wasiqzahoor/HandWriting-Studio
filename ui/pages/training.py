"""Training / profile creation wizard (spec 24-25).

6 honest steps: Upload -> Analyze -> Coverage -> Build -> Validate -> Save.
No fake OCR: coverage is user-confirmed; analysis reports real image metrics.
Build runs off the UI thread.
"""
import os

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QListWidget, QFileDialog, QLineEdit, QComboBox,
                               QSpinBox, QCheckBox, QGridLayout, QGroupBox,
                               QFormLayout, QProgressBar)
from PySide6.QtCore import Qt, QThread, Signal

from ui.components import (PageHeader, Card, primary_button, ghost_button)
from training.analyzer import analyze_sample
from training.builder import build_profile, PRINTABLE
from training.validator import validate_new_profile
from handwriting_engine.glyph_manager import find_handwriting_font


class BuildWorker(QThread):
    done = Signal(object, object)
    failed = Signal(str)

    def __init__(self, args):
        super().__init__()
        self.args = args

    def run(self):
        try:
            sup, skip = build_profile(*self.args)
            self.done.emit(sup, skip)
        except Exception as e:
            self.failed.emit(f"{type(e).__name__}: {e}")


GROUPS = {"Uppercase A-Z": [chr(c) for c in range(65, 91)],
          "Lowercase a-z": [chr(c) for c in range(97, 123)],
          "Digits 0-9": [chr(c) for c in range(48, 58)],
          "Punctuation": list(".,?!'\"-:;()&")}


class TrainingPage(QWidget):
    def __init__(self, ctx, win):
        super().__init__()
        self.ctx = ctx
        self.win = win
        self.samples = []
        self.analyses = []
        self.worker = None
        self.built_id = None

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)
        root.addWidget(PageHeader(
            "Create Handwriting Profile",
            "Upload samples, analyze, confirm coverage, build and validate."))
        from PySide6.QtWidgets import QScrollArea
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        holder = QWidget()
        holder.setObjectName("scrollbody")
        self.steps = QVBoxLayout(holder)
        self.steps.setContentsMargins(0, 0, 0, 0)
        self.steps.setSpacing(12)
        sc.setWidget(holder)
        root.addWidget(sc, 1)
        self._build_steps()
        self.refresh()

    # ------------------------------------------------------------------ UI
    def _step_card(self, num, title):
        c = Card()
        h = QLabel(f"Step {num} - {title}")
        h.setStyleSheet("font-weight: 800; font-size: 14px;")
        c.layout().addWidget(h)
        self.steps.addWidget(c)
        return c

    def _build_steps(self):
        # 1 upload
        c1 = self._step_card(1, "Upload Samples")
        row = QHBoxLayout()
        add = ghost_button("Add Images")
        add.clicked.connect(self.add_samples)
        clr = ghost_button("Clear")
        clr.clicked.connect(lambda: (self.samples.clear(),
                                     self.analyses.clear(), self.refresh()))
        row.addWidget(add)
        row.addWidget(clr)
        row.addStretch(1)
        c1.layout().addLayout(row)
        self.sample_list = QListWidget()
        self.sample_list.setMaximumHeight(90)
        c1.layout().addWidget(self.sample_list)

        # 2 analyze
        c2 = self._step_card(2, "Analyze Samples")
        self.btn_analyze = ghost_button("Run Analysis")
        self.btn_analyze.clicked.connect(self.run_analysis)
        c2.layout().addWidget(self.btn_analyze)
        self.analysis_lbl = QLabel("No analysis yet.")
        self.analysis_lbl.setProperty("class", "muted")
        self.analysis_lbl.setWordWrap(True)
        c2.layout().addWidget(self.analysis_lbl)

        # 3 coverage
        c3 = self._step_card(3, "Character Coverage (confirm what the "
                                "samples contain)")
        self.cov_checks = {}
        grid = QGridLayout()
        for i, (g, chars) in enumerate(GROUPS.items()):
            cb = QCheckBox(f"{g} ({len(chars)})")
            cb.setChecked(True)
            self.cov_checks[g] = (cb, chars)
            grid.addWidget(cb, i // 2, i % 2)
        c3.layout().addLayout(grid)
        self.cov_lbl = QLabel("")
        self.cov_lbl.setProperty("class", "muted")
        c3.layout().addWidget(self.cov_lbl)

        # 4 build
        c4 = self._step_card(4, "Train / Build Profile")
        form = QFormLayout()
        self.ed_name = QLineEdit("My Handwriting")
        self.ed_author = QLineEdit("Author name")
        self.cmb_font = QComboBox()
        fonts = [f for f in
                 [r"C:\Windows\Fonts\segoesc.ttf",
                  r"C:\Windows\Fonts\segoepr.ttf",
                  r"C:\Windows\Fonts\LHANDW.TTF",
                  r"C:\Windows\Fonts\BRUSHSCI.TTF"] if os.path.isfile(f)] or (
                     [find_handwriting_font()] if find_handwriting_font()
                     else [])
        for f in fonts:
            self.cmb_font.addItem(os.path.basename(f), f)
        self.spin_var = QSpinBox()
        self.spin_var.setRange(1, 5)
        self.spin_var.setValue(3)
        form.addRow("Profile name:", self.ed_name)
        form.addRow("Author:", self.ed_author)
        form.addRow("Base font:", self.cmb_font)
        form.addRow("Variants per glyph:", self.spin_var)
        c4.layout().addLayout(form)
        self.btn_build = primary_button("Build Profile")
        self.btn_build.clicked.connect(self.build)
        c4.layout().addWidget(self.btn_build)
        self.build_bar = QProgressBar()
        self.build_bar.setRange(0, 0)
        self.build_bar.setVisible(False)
        c4.layout().addWidget(self.build_bar)

        # 5 validate
        c5 = self._step_card(5, "Validate")
        self.valid_lbl = QLabel("Build a profile first.")
        self.valid_lbl.setProperty("class", "muted")
        self.valid_lbl.setWordWrap(True)
        c5.layout().addWidget(self.valid_lbl)

        # 6 save
        c6 = self._step_card(6, "Save Profile")
        self.save_lbl = QLabel("The profile is saved into the app profile "
                               "library and appears on the Profiles page.")
        self.save_lbl.setProperty("class", "muted")
        self.save_lbl.setWordWrap(True)
        c6.layout().addWidget(self.save_lbl)
        row6 = QHBoxLayout()
        self.btn_use = primary_button("Set as Default Profile")
        self.btn_use.clicked.connect(self.use_built)
        self.btn_use.setEnabled(False)
        row6.addWidget(self.btn_use)
        row6.addStretch(1)
        c6.layout().addLayout(row6)

    # -------------------------------------------------------------- actions
    def add_samples(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select handwriting samples", "",
            "Images (*.png *.jpg *.jpeg)")
        self.samples.extend(p for p in paths if p not in self.samples)
        self.refresh()

    def refresh(self):
        self.sample_list.clear()
        self.sample_list.addItems(self.samples)
        total = sum(len(chars) for cb, chars in self.cov_checks.values()
                    if cb.isChecked()) if hasattr(self, "cov_checks") else 0
        if hasattr(self, "cov_lbl"):
            self.cov_lbl.setText(f"Selected character set: {total} characters.")

    def run_analysis(self):
        if not self.samples:
            self.win.toast("Add at least one sample image.", "warn")
            return
        try:
            self.analyses = [analyze_sample(p) for p in self.samples]
        except Exception as e:
            self.win.toast(f"Analysis failed: {e}", "error")
            return
        lines = []
        for a in self.analyses:
            lines.append(f"{os.path.basename(a['path'])}: "
                         f"{a['size'][0]}x{a['size'][1]}, ink rgb{a['ink']}, "
                         f"coverage {a['ink_coverage'] * 100:.1f}%, "
                         f"stroke ~{a['stroke_px']}px. {a['verdict']}")
        self.analysis_lbl.setText("\n".join(lines))
        self.win.toast("Sample analysis complete.")

    def selected_charset(self):
        out = []
        for cb, chars in self.cov_checks.values():
            if cb.isChecked():
                out.extend(chars)
        return out

    def build(self):
        if not self.analyses:
            self.win.toast("Run sample analysis first (step 2).", "warn")
            return
        charset = self.selected_charset()
        if not charset:
            self.win.toast("Select at least one character group.", "warn")
            return
        base = self.cmb_font.currentData() or find_handwriting_font()
        if not base:
            self.win.toast("No handwriting base font found.", "error")
            return
        name = self.ed_name.text().strip() or "My Handwriting"
        pid = "".join(c if (c.isalnum() or c in "-_") else "-"
                      for c in name.lower()).strip("-") or "custom"
        if pid in self.ctx.profiles.list_ids():
            self.win.toast(f"Profile id '{pid}' already exists.", "error")
            return
        # ink = median of sample inks
        inks = [a["ink"] for a in self.analyses]
        ink = tuple(int(sum(c) / len(c)) for c in zip(*inks))
        dest = os.path.join(self.ctx.paths.profiles, pid)
        self.build_bar.setVisible(True)
        self.btn_build.setEnabled(False)
        self.worker = BuildWorker((dest, name, self.ed_author.text().strip(),
                                   base, ink, charset,
                                   int(self.spin_var.value()), 7))
        self.worker.done.connect(
            lambda sup, skip: self._built(pid, sup, skip))
        self.worker.failed.connect(self._build_failed)
        self.worker.start()

    def _built(self, pid, supported, skipped):
        self.build_bar.setVisible(False)
        self.btn_build.setEnabled(True)
        self.built_id = pid
        rep = validate_new_profile(self.ctx.paths.profiles, pid,
                                   self.selected_charset())
        msg = (f"Built '{pid}': {rep['supported']} chars, "
               f"{rep['glyph_files']} files. ")
        if rep["warnings"]:
            msg += "Warnings:\n" + "\n".join(rep["warnings"])
            self.win.toast("Profile built with warnings - see step 5.",
                           "warn")
        else:
            msg += "Validation passed."
            self.win.toast("Profile built and validated.")
        self.valid_lbl.setText(msg)
        self.btn_use.setEnabled(True)

    def _build_failed(self, msg):
        self.build_bar.setVisible(False)
        self.btn_build.setEnabled(True)
        self.win.toast(f"Build failed: {msg}", "error")

    def use_built(self):
        if self.built_id:
            self.ctx.settings.set("default_profile", self.built_id)
            self.win.toast(f"Default profile: {self.built_id}")
