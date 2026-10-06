"""Document Creator (spec 17-18): settings | preview | export actions."""
import datetime
import os
import random

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                               QLabel, QTextEdit, QLineEdit, QComboBox,
                               QSpinBox, QSlider, QScrollArea, QGroupBox,
                               QFormLayout, QCheckBox, QSizePolicy, QFrame,
                               QFileDialog)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PIL import Image
from PIL.ImageQt import ImageQt

from ui.components import (PageHeader, primary_button, export_button,
                           ghost_button)


class RenderWorker(QThread):
    done = Signal(object, object, object)
    failed = Signal(str)

    def __init__(self, ctx, template_id, fields, profile_id, settings):
        super().__init__()
        self.ctx = ctx
        self.args = (template_id, fields, profile_id, settings)

    def run(self):
        try:
            tid, fields, pid, st = self.args
            pages, warnings, info = self.ctx.documents.render_paginated(
                tid, fields, pid, st)
            self.done.emit(pages, warnings, info)
        except Exception as e:
            self.failed.emit(f"{type(e).__name__}: {e}")


class DocumentCreatorPage(QWidget):
    def __init__(self, ctx, win):
        super().__init__()
        self.ctx = ctx
        self.win = win
        self.pages = []       # full-res PIL pages of last render
        self.page_idx = 0
        self.zoom = None      # None = fit whole page in view
        self.info = {}
        self.worker = None

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)
        head = PageHeader("Document Creator",
                          "Select a template and profile, write text, preview, export.")
        root.addWidget(head)

        split = QSplitter(Qt.Horizontal)
        root.addWidget(split, 1)

        # ---- settings panel ----
        left = QFrame()
        left.setProperty("class", "card")
        ll = QVBoxLayout(left)
        form = QFormLayout()
        form.setSpacing(10)
        self.cmb_template = QComboBox()
        self.cmb_template.setToolTip("Document template (4x6 card or #10 envelope)")
        self.cmb_template.currentIndexChanged.connect(self._template_changed)
        self.cmb_profile = QComboBox()
        self.cmb_profile.setToolTip("Handwriting style for this document")
        form.addRow("Template:", self.cmb_template)
        form.addRow("Handwriting Profile:", self.cmb_profile)
        ll.addLayout(form)

        self.field_widgets = {}
        self.field_boxes = {}
        self.fields_box = QVBoxLayout()
        self.fields_box.setSpacing(8)
        ll.addLayout(self.fields_box)

        self.sl_size = self._slider(ll, "Size", 20, 64,
                                    ctx.settings.get("default_font_size", 42))
        self.sl_spacing = self._slider(ll, "Spacing", -6, 12, 0)
        self.sl_slant = self._slider(ll, "Slant", -25, 25, 8)
        self.sl_variation = self._slider(
            ll, "Variation", 0, 100,
            int(ctx.settings.get("default_variation", 0.6) * 100))

        adv = QGroupBox("Advanced Settings")
        adv.setCheckable(True)
        adv.setChecked(False)
        af = QFormLayout(adv)
        self.sl_baseline = self._slider(af, "Baseline var.", 0, 150, 100,
                                        wrap=True)
        self.sl_stroke = self._slider(af, "Stroke var.", 0, 150, 100,
                                      wrap=True)
        ll.addWidget(adv)

        seed_row = QHBoxLayout()
        seed_row.addWidget(QLabel("Seed:"))
        self.spin_seed = QSpinBox()
        self.spin_seed.setRange(0, 999999)
        self.spin_seed.setValue(12345)
        seed_row.addWidget(self.spin_seed, 1)
        b_rand = ghost_button("Randomize")
        b_rand.clicked.connect(
            lambda: self.spin_seed.setValue(random.randint(0, 999999)))
        seed_row.addWidget(b_rand)
        ll.addLayout(seed_row)
        ll.addStretch(1)
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setWidget(left)
        left_scroll.setMinimumWidth(360)
        split.addWidget(left_scroll)

        # ---- preview ----
        mid = QFrame()
        mid.setProperty("class", "card")
        ml = QVBoxLayout(mid)
        cap = QHBoxLayout()
        self.lbl_cap = QLabel("PREVIEW")
        self.lbl_cap.setStyleSheet("font-weight:800;letter-spacing:1px;")
        cap.addWidget(self.lbl_cap)
        cap.addStretch(1)
        self.lbl_size = QLabel("")
        self.lbl_size.setProperty("class", "sizebadge")
        cap.addWidget(self.lbl_size)
        ml.addLayout(cap)
        # zoom + pager toolbar
        tools = QHBoxLayout()
        tools.setSpacing(6)
        self.btn_zout = ghost_button("\u2212")
        self.btn_zout.setFixedWidth(38)
        self.btn_zout.setToolTip("Zoom out (Ctrl+-)")
        self.btn_zout.setShortcut("Ctrl+-")
        self.btn_zout.clicked.connect(lambda: self.bump_zoom(1 / 1.25))
        self.lbl_zoom = QLabel("Fit")
        self.lbl_zoom.setMinimumWidth(52)
        self.lbl_zoom.setAlignment(Qt.AlignCenter)
        self.lbl_zoom.setProperty("class", "sizebadge")
        self.btn_zin = ghost_button("+")
        self.btn_zin.setFixedWidth(38)
        self.btn_zin.setToolTip("Zoom in (Ctrl+=), Ctrl+wheel works too")
        self.btn_zin.setShortcut("Ctrl+=")
        self.btn_zin.clicked.connect(lambda: self.bump_zoom(1.25))
        self.btn_fit = ghost_button("Fit")
        self.btn_fit.setToolTip("Fit whole page in view (Ctrl+0)")
        self.btn_fit.setShortcut("Ctrl+0")
        self.btn_fit.clicked.connect(self.zoom_fit)
        tools.addWidget(self.btn_zout)
        tools.addWidget(self.lbl_zoom)
        tools.addWidget(self.btn_zin)
        tools.addWidget(self.btn_fit)
        tools.addStretch(1)
        self.btn_prev = ghost_button("\u25c0")
        self.btn_prev.setFixedWidth(38)
        self.btn_prev.setToolTip("Previous page")
        self.btn_prev.clicked.connect(lambda: self.turn_page(-1))
        self.lbl_page = QLabel("—")
        self.lbl_page.setMinimumWidth(86)
        self.lbl_page.setAlignment(Qt.AlignCenter)
        self.lbl_page.setProperty("class", "sizebadge")
        self.btn_next = ghost_button("\u25b6")
        self.btn_next.setFixedWidth(38)
        self.btn_next.setToolTip("Next page")
        self.btn_next.clicked.connect(lambda: self.turn_page(1))
        tools.addWidget(self.btn_prev)
        tools.addWidget(self.lbl_page)
        tools.addWidget(self.btn_next)
        for b in (self.btn_zout, self.btn_zin, self.btn_fit, self.btn_prev,
                  self.btn_next):
            b.setEnabled(False)
        ml.addLayout(tools)
        self.view = QLabel("Press Generate to render a preview.")
        self.view.setObjectName("docframe")
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setMinimumSize(360, 520)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setWidget(self.view)
        sc.viewport().installEventFilter(self)
        self.preview_scroll = sc
        ml.addWidget(sc, 1)
        split.addWidget(mid)
        split.setSizes([380, 620])
        split.setStretchFactor(1, 1)

        # ---- actions ----
        bar = QHBoxLayout()
        bar.setSpacing(10)
        self.btn_gen = primary_button("Generate Preview")
        self.btn_gen.setToolTip("Render the document (Ctrl+G)")
        self.btn_gen.setShortcut("Ctrl+G")
        self.btn_gen.setMinimumHeight(44)
        self.btn_gen.clicked.connect(self.generate)
        self.btn_pdf = export_button("Export PDF")
        self.btn_png = export_button("Export PNG")
        self.btn_pdf.clicked.connect(lambda: self.export(["pdf"]))
        self.btn_png.clicked.connect(lambda: self.export(["png"]))
        self.btn_pdf.setEnabled(False)
        self.btn_png.setEnabled(False)
        bar.addWidget(self.btn_gen, 2)
        bar.addWidget(self.btn_pdf, 1)
        bar.addWidget(self.btn_png, 1)
        root.addLayout(bar)
        self.reload_options()
        self._template_changed()

    # ------------------------------------------------------------- setup ---
    def _slider(self, parent_layout, label, lo, hi, val, wrap=False):
        row = QHBoxLayout() if wrap else None
        lab = QLabel(label)
        lab.setProperty("class", "muted")
        s = QSlider(Qt.Horizontal)
        s.setRange(lo, hi)
        s.setValue(val)
        badge = QLabel(str(val))
        badge.setMinimumWidth(34)
        if isinstance(parent_layout, QFormLayout):
            w = QWidget()
            lay = QHBoxLayout(w)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(s, 1)
            lay.addWidget(badge)
            parent_layout.addRow(lab, w)
        else:
            parent_layout.addWidget(lab)
            h = QHBoxLayout()
            h.addWidget(s, 1)
            h.addWidget(badge)
            parent_layout.addLayout(h)
        s.valueChanged.connect(lambda v: badge.setText(str(v)))
        setattr(self, f"_sl_{label}", s)
        return s

    def reload_options(self):
        st = self.ctx.settings
        keep_tpl = self.cmb_template.currentData()
        keep_prof = self.cmb_profile.currentData()
        keep_fields = {}
        for k, get in self.field_widgets.items():
            try:
                keep_fields[k] = get()
            except Exception:
                pass
        self.cmb_template.blockSignals(True)
        self.cmb_template.clear()
        for t in self.ctx.templates.list():
            self.cmb_template.addItem(f"{t.name}  ({t.width_in} x "
                                      f"{t.height_in} in)", t.template_id)
        dflt = keep_tpl or st.get("default_template")
        idx = self.cmb_template.findData(dflt)
        self.cmb_template.setCurrentIndex(max(0, idx))
        self.cmb_template.blockSignals(False)
        self.cmb_profile.blockSignals(True)
        self.cmb_profile.clear()
        for p in self.ctx.profiles.list_profiles():
            self.cmb_profile.addItem(f"{p['meta'].get('name', p['id'])}  "
                                     f"v{p['meta'].get('version', '?')}",
                                     p["id"])
        want = keep_prof or st.get("default_profile") or \
            self.ctx.default_profile_id()
        idx = self.cmb_profile.findData(want)
        self.cmb_profile.setCurrentIndex(max(0, idx))
        self.cmb_profile.blockSignals(False)
        # restore field text for keys that still exist
        for k, v in keep_fields.items():
            if k in self.field_widgets:
                pass  # widgets rebuilt below; reapply after template sync
        self._saved_fields = keep_fields
        self._template_changed()
        for k, v in (self._saved_fields or {}).items():
            w = self._field_widget(k)
            if w is not None:
                try:
                    if hasattr(w, "setPlainText"):
                        w.setPlainText(v)
                    else:
                        w.setText(v)
                except Exception:
                    pass

    def current_template(self):
        return self.ctx.templates.get(self.cmb_template.currentData())

    def _template_changed(self):
        # rebuild field editors for the template kind
        for i in reversed(range(self.fields_box.count())):
            item = self.fields_box.takeAt(i)
            if item.widget():
                item.widget().deleteLater()
        self.field_widgets = {}
        self.field_boxes = {}
        try:
            tpl = self.current_template()
        except Exception:
            return
        self.lbl_size.setText(f"{tpl.width_in} x {tpl.height_in} in")
        if tpl.kind == "envelope":
            self._add_field("sender", "Sender:", 3,
                            "Alex Johnson\n1 Main St\nSpringfield")
            self._add_field("recipient", "Recipient:", 4,
                            "John Smith\n123 Oak Ave\nShelbyville")
        else:
            self._add_field("header", "Header:", 1, "Alex Johnson")
            self._add_field("body", "Text:", 8,
                            "Dear John,\n\nThank you for your message.\n\n"
                            "Best regards,\nAlex")

    def _add_field(self, key, label, lines, default):
        lab = QLabel(label)
        lab.setProperty("class", "muted")
        if lines <= 1:
            w = QLineEdit(default)
            w.setMinimumHeight(34)
            get = w.text
        else:
            w = QTextEdit(default)
            w.setMinimumHeight(28 * lines)
            get = w.toPlainText
        self.fields_box.addWidget(lab)
        self.fields_box.addWidget(w)
        self.field_widgets[key] = get
        self.field_boxes[key] = w

    def _field_widget(self, key):
        return self.field_boxes.get(key)

    def use_template(self, template_id):
        self.reload_options()
        for i in range(self.cmb_template.count()):
            if self.cmb_template.itemData(i) == template_id:
                self.cmb_template.setCurrentIndex(i)
        self.win.goto(1)

    # ------------------------------------------------------------ actions ---
    def collect(self):
        tpl = self.current_template()
        fields = {k: get() for k, get in self.field_widgets.items()}
        settings = {
            "font_size": self.sl_size.value(),
            "spacing": self.sl_spacing.value(),
            "slant": self.sl_slant.value() / 100.0,
            "variation": self.sl_variation.value() / 100.0,
            "seed": int(self.spin_seed.value()),
            "baseline_jitter": self.sl_baseline.value() / 100.0,
            "stroke_jitter": self.sl_stroke.value() / 100.0,
            "dpi": self.ctx.settings.get("dpi", 300),
            "sample_path": None,
        }
        return tpl, fields, self.cmb_profile.currentData(), settings

    def generate(self):
        try:
            tpl, fields, pid, st = self.collect()
        except Exception as e:
            self.win.toast(f"Cannot render: {e}", "error")
            return
        if not any((v or "").strip() for v in fields.values()):
            self.win.toast("Please enter some text first.", "warn")
            return
        self.btn_gen.setEnabled(False)
        self.btn_gen.setText("Rendering...")
        self.worker = RenderWorker(self.ctx, tpl.template_id, fields, pid,
                                   st)
        self.worker.done.connect(self._done)
        self.worker.failed.connect(self._failed)
        self.worker.start()

    def _done(self, pages, warnings, info):
        self.btn_gen.setEnabled(True)
        self.btn_gen.setText("Generate Preview")
        self.pages = pages
        self.page_idx = 0
        self.zoom = None  # None = fit whole page
        self.info = info
        self._update_preview()
        for b in (self.btn_pdf, self.btn_png, self.btn_zout, self.btn_zin,
                  self.btn_fit, self.btn_prev, self.btn_next):
            b.setEnabled(True)
        self._sync_pager()
        for w in warnings:
            self.win.toast(w, "warn")
        if not warnings:
            n = len(pages)
            self.win.toast(f"Document generated successfully "
                           f"({n} page{'s' if n > 1 else ''}).")
        self.ctx.db.add_document(
            f"{info.get('template', 'doc')}_{info['seed']}",
            info.get("template", ""), info.get("profile", ""),
            info["seed"], "preview", "")

    def _failed(self, msg):
        self.btn_gen.setEnabled(True)
        self.btn_gen.setText("Generate Preview")
        self.win.toast(f"Render failed: {msg}", "error")

    def export(self, formats):
        if not self.pages:
            self.win.toast("Generate a preview first.", "warn")
            return
        st = self.ctx.settings
        tpl, _fields, pid, settings = self.collect()
        outdir = st.get("export_dir") or self.ctx.paths.exports
        os.makedirs(outdir, exist_ok=True)
        base = self.ctx.exports.build_name(
            st.get("naming", "{template}_{profile}_{seed}_{date}"),
            tpl.template_id, pid, settings["seed"], "x").rsplit(".", 1)[0]
        try:
            paths = self.ctx.exports.export(
                self.pages, self.info["size_in"], outdir, base, formats,
                doc_type="document", template=tpl.template_id, profile=pid)
            self.win.toast(f"Exported: {', '.join(os.path.basename(p) for p in paths)}")
        except Exception as e:
            self.win.toast(f"Export failed: {e}", "error")

    # ------------------------------------------------- pager / zoom ---
    def _sync_pager(self):
        n = len(self.pages)
        self.lbl_page.setText(f"{self.page_idx + 1} / {n}" if n else "—")
        multi = n > 1
        self.btn_prev.setEnabled(multi and self.page_idx > 0)
        self.btn_next.setEnabled(multi and self.page_idx < n - 1)

    def turn_page(self, delta):
        if not self.pages:
            return
        self.page_idx = max(0, min(len(self.pages) - 1,
                                   self.page_idx + delta))
        self._update_preview()
        self._sync_pager()

    def bump_zoom(self, factor):
        if not self.pages:
            return
        cur = self._current_factor()
        self.zoom = max(0.15, min(4.0, cur * factor))
        self._update_preview()

    def zoom_fit(self):
        self.zoom = None
        self._update_preview()

    def _current_factor(self):
        if self.zoom is not None:
            return self.zoom
        return self._fit_factor()

    def _fit_factor(self):
        if not self.pages:
            return 1.0
        vp = self.preview_scroll.viewport().size()
        img = self.pages[self.page_idx]
        s = min(max(1, vp.width() - 28) / img.width,
                max(1, vp.height() - 28) / img.height)
        return max(0.05, min(s, 2.0))

    def _update_preview(self):
        if not self.pages:
            return
        img = self.pages[self.page_idx]
        f = self.zoom if self.zoom is not None else self._fit_factor()
        dw, dh = max(1, int(img.width * f)), max(1, int(img.height * f))
        prev = img.resize((dw, dh), Image.LANCZOS)
        if prev.mode == "RGBA":
            bg = Image.new("RGB", prev.size, (255, 255, 255))
            bg.paste(prev, mask=prev.split()[-1])
            prev = bg
        self.view.setPixmap(QPixmap.fromImage(ImageQt(prev)))
        self.lbl_zoom.setText("Fit" if self.zoom is None
                              else f"{int(round(f * 100))}%")
        self._sync_pager()

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self.preview_scroll.viewport():
            if event.type() == QEvent.Resize and self.zoom is None \
                    and self.pages:
                self._update_preview()
            elif event.type() == QEvent.Wheel and self.pages and \
                    event.modifiers() & Qt.ControlModifier:
                steps = event.angleDelta().y() / 120.0
                if steps:
                    self.bump_zoom(1.25 ** steps)
                return True
        return super().eventFilter(obj, event)

    def refresh(self):
        self.reload_options()
