"""Document Creator (spec 17-18): settings | preview | export actions."""
import datetime
import os
import random

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                               QLabel, QTextEdit, QLineEdit, QComboBox,
                               QPushButton, QButtonGroup,
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
        self.editor = None    # inline page editor overlay
        self.editor_entry = None
        self.editor_cancelled = False
        self.hover_line = None
        self._disp_factor = 1.0

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
        self.cmb_profile.currentIndexChanged.connect(
            lambda: self._profile_changed())
        form.addRow("Template:", self.cmb_template)
        form.addRow("Handwriting Profile:", self.cmb_profile)
        ll.addLayout(form)

        self.field_widgets = {}
        self.field_boxes = {}
        self.fields_box = QVBoxLayout()
        self.fields_box.setSpacing(8)
        ll.addLayout(self.fields_box)

        self.sl_size = self._slider(ll, "Size", 8, 72,
                                    ctx.settings.get("default_font_size", 42),
                                    suffix_fn=lambda v: f"{v} px \u00b7 "
                                                       f"{v * 72 // 300} pt")
        self.sl_spacing = self._slider(ll, "Spacing", -6, 12, 0)
        self.sl_slant = self._slider(ll, "Slant", -25, 25, 8)
        self.sl_variation = self._slider(
            ll, "Variation", 0, 100,
            int(ctx.settings.get("default_variation", 0.6) * 100))

        # ---- ink + page ----
        ink_lbl = QLabel("Ink color")
        ink_lbl.setProperty("class", "muted")
        ll.addWidget(ink_lbl)
        ink_row = QHBoxLayout()
        ink_row.setSpacing(8)
        from PySide6.QtWidgets import QButtonGroup
        self.ink_group = QButtonGroup(self)
        self.ink_group.setExclusive(True)
        self.ink = (35, 35, 40)
        self._ink_custom = False
        for i, (nm, rgb) in enumerate(
                [("Black", (35, 35, 40)), ("Blue", (30, 42, 92)),
                 ("Red", (193, 18, 31)), ("Green", (31, 122, 92))]):
            b = QPushButton()
            b.setCheckable(True)
            b.setFixedSize(30, 30)
            b.setToolTip(f"{nm} ink")
            b.setStyleSheet(
                f"QPushButton {{ background: rgb{rgb}; border-radius: 15px;"
                f" border: 2px solid transparent; }}"
                f"QPushButton:checked {{ border: 2px solid #E63946; }}")
            b.setProperty("ink", rgb)
            b.clicked.connect(lambda _=False, c=rgb: self._set_ink(c, True))
            self.ink_group.addButton(b, i)
            ink_row.addWidget(b)
        self.ink_group.buttons()[0].setChecked(True)
        b_custom = ghost_button("Custom...")
        b_custom.setToolTip("Pick any pen color")
        b_custom.clicked.connect(self.pick_ink)
        ink_row.addWidget(b_custom, 1)
        ll.addLayout(ink_row)

        page_row = QHBoxLayout()
        page_row.setSpacing(14)
        from PySide6.QtWidgets import QCheckBox
        self.ck_ruled = QCheckBox("Ruled lines")
        self.ck_ruled.setToolTip("Show notebook lines under the text")
        self.ck_white = QCheckBox("White page")
        self.ck_white.setToolTip("Pure white paper instead of warm card")
        page_row.addWidget(self.ck_ruled)
        page_row.addWidget(self.ck_white)
        page_row.addStretch(1)
        ll.addLayout(page_row)

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
        left_scroll.setMinimumWidth(340)
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
        # Centered page holder: the page keeps its aspect, gets even margins
        # on all sides and is never clipped by the frame. A soft shadow
        # lifts it off the surface like a real sheet of paper.
        self.view = QLabel("Press Generate to render a preview.\n\n"
                           "Tip: after rendering, click any line on the page "
                           "to edit it right there.")
        self.view.setObjectName("docframe")
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setMinimumSize(280, 420)
        self.view.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.view.setCursor(Qt.ArrowCursor)
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self.view)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 6)
        shadow.setColor(Qt.gray)
        self.view.setGraphicsEffect(shadow)
        self.view.installEventFilter(self)
        self.view.setMouseTracking(True)
        holder = QWidget()
        holder_layout = QVBoxLayout(holder)
        holder_layout.setContentsMargins(18, 18, 18, 18)
        holder_layout.setSpacing(0)
        holder_layout.addWidget(self.view, 0, Qt.AlignCenter)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setWidget(holder)
        sc.viewport().installEventFilter(self)
        self.preview_scroll = sc
        ml.addWidget(sc, 1)
        # hover highlight + inline editor live on the page itself
        self.hover_frame = QFrame(self.view)
        self.hover_frame.setStyleSheet(
            "background: rgba(230,57,70,14);"
            "border: 2px solid rgba(230,57,70,220); border-radius: 4px;")
        self.hover_frame.hide()
        self.hover_line = None
        self.editor = None
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
    def _slider(self, parent_layout, label, lo, hi, val, wrap=False,
                suffix_fn=None):
        row = QHBoxLayout() if wrap else None
        lab = QLabel(label)
        lab.setProperty("class", "muted")
        s = QSlider(Qt.Horizontal)
        s.setRange(lo, hi)
        s.setValue(val)
        badge = QLabel((suffix_fn(val) if suffix_fn else str(val)))
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
        s.valueChanged.connect(
            lambda v: badge.setText(suffix_fn(v) if suffix_fn else str(v)))
        setattr(self, f"_sl_{label}", s)
        return s

    def pick_ink(self):
        from PySide6.QtWidgets import QColorDialog
        from PySide6.QtGui import QColor
        cur = QColor(*self.ink)
        col = QColorDialog.getColor(cur, self, "Pen ink color")
        if col.isValid():
            self._set_ink((col.red(), col.green(), col.blue()), True)
            self.win.toast(f"Ink set to rgb{self.ink}.")

    def _set_ink(self, rgb, custom):
        self.ink = tuple(rgb)
        self._ink_custom = bool(custom)

    def _profile_changed(self):
        if getattr(self, "_ink_custom", False):
            return
        try:
            pid = self.cmb_profile.currentData()
            prof = self.ctx.profiles.get(pid)
            ink = tuple(prof.get("config", {}).get("ink", [35, 35, 40]))
            self._set_ink(ink, False)
            for b in self.ink_group.buttons():
                b.setChecked(tuple(b.property("ink")) == tuple(ink))
        except Exception:
            pass

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
        self._profile_changed()
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
        # rebuild field editors + page options for the template
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
        if getattr(self, "_last_tpl", None) != tpl.template_id:
            self.ck_ruled.setChecked(bool(tpl.ruled))
            self.ck_white.setChecked(bool(tpl.page_white))
            self._last_tpl = tpl.template_id
        presets = {
            "header": ("Header:", 1, "Alex Johnson"),
            "body": ("Text:", 8, "Dear John,\n\nThank you for your message.\n\n"
                                 "Best regards,\nAlex"),
            "sender": ("Sender:", 3, "Alex Johnson\n1 Main St\nSpringfield"),
            "recipient": ("Recipient:", 4, "John Smith\n123 Oak Ave\n"
                                           "Shelbyville"),
        }
        for key in tpl.fields:
            label, lines, default = presets.get(
                key, (f"{key.capitalize()}:", 4, ""))
            self._add_field(key, label, lines, default)

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
            "ink": tuple(self.ink),
            "ruled": bool(self.ck_ruled.isChecked()),
            "page_white": bool(self.ck_white.isChecked()),
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
        s = min(max(1, vp.width() - 52) / img.width,
                max(1, vp.height() - 52) / img.height)
        return max(0.05, min(s, 2.0))

    def _update_preview(self):
        if not self.pages:
            return
        self._close_editor(commit=False)
        img = self.pages[self.page_idx]
        f = self.zoom if self.zoom is not None else self._fit_factor()
        dw, dh = max(1, int(img.width * f)), max(1, int(img.height * f))
        prev = img.resize((dw, dh), Image.LANCZOS)
        if prev.mode == "RGBA":
            bg = Image.new("RGB", prev.size, (255, 255, 255))
            bg.paste(prev, mask=prev.split()[-1])
            prev = bg
        self.view.setPixmap(QPixmap.fromImage(ImageQt(prev)))
        self.view.setFixedSize(dw, dh)
        self._disp_factor = dw / img.width
        self.lbl_zoom.setText("Fit" if self.zoom is None
                              else f"{int(round(f * 100))}%")
        self.hover_frame.hide()
        self.hover_line = None
        self.view.setCursor(Qt.ArrowCursor)
        self._sync_pager()

    # -------------------------------------------- direct page editing ---
    def _page_point(self, view_pos):
        """View coords -> full-res page coords (or None when no page)."""
        if not self.pages or not self.view.pixmap():
            return None
        pm = self.view.pixmap()
        ox = (self.view.width() - pm.width()) // 2
        oy = (self.view.height() - pm.height()) // 2
        px = (view_pos.x() - ox) / self._disp_factor
        py = (view_pos.y() - oy) / self._disp_factor
        img = self.pages[self.page_idx]
        if 0 <= px < img.width and 0 <= py < img.height:
            return (px, py)
        return None

    def _line_at(self, page_pt):
        if page_pt is None:
            return None
        px, py = page_pt
        for entry in self.info.get("map", []):
            if entry["page"] != self.page_idx:
                continue
            x0, y0, x1, y1 = entry["rect"]
            if x0 - 6 <= px <= x1 + 20 and y0 - 4 <= py <= y1 + 4:
                return entry
        return None

    def _show_hover(self, entry):
        if entry is None:
            self.hover_frame.hide()
            self.hover_line = None
            self.view.setCursor(Qt.ArrowCursor)
            self.view.setToolTip("")
            return
        f = self._disp_factor
        x0, y0, x1, y1 = entry["rect"]
        pm = self.view.pixmap()
        ox = (self.view.width() - pm.width()) // 2
        oy = (self.view.height() - pm.height()) // 2
        self.hover_frame.setGeometry(int(ox + x0 * f) - 3, int(oy + y0 * f) - 2,
                                     int((x1 - x0) * f) + 6,
                                     int((y1 - y0) * f) + 4)
        self.hover_frame.show()
        self.hover_line = entry
        self.view.setCursor(Qt.IBeamCursor)
        self.view.setToolTip("Click to edit this line")

    def _open_editor(self, entry):
        if entry is None or self.editor is not None:
            return
        f = self._disp_factor
        x0, y0, x1, y1 = entry["rect"]
        pm = self.view.pixmap()
        ox = (self.view.width() - pm.width()) // 2
        oy = (self.view.height() - pm.height()) // 2
        from PySide6.QtWidgets import QTextEdit
        ed = QTextEdit(self.view)
        ed.setGeometry(int(ox + x0 * f) - 4, int(oy + y0 * f) - 4,
                       max(220, int((x1 - x0) * f) + 8),
                       max(64, int((y1 - y0) * f) + 8))
        try:
            fs = max(9, int(self.collect()[0].base_font_size * f))
        except Exception:
            fs = 12
        ed.setStyleSheet(f"background: white; color: #111113; "
                         f"font-size: {fs}px; border: 2px solid #E63946; "
                         f"border-radius: 6px; padding: 4px;")
        paras = (self._area_text(entry["area"]) or "").split("\n")
        ed.setPlainText(paras[entry["para"]] if entry["para"] < len(paras)
                        else "")
        ed.installEventFilter(self)
        ed.show()
        ed.setFocus()
        ed.selectAll()
        self.editor = ed
        self.editor_entry = entry
        self.editor_cancelled = False
        self.hover_frame.hide()

    def _area_text(self, key):
        get = self.field_widgets.get(key)
        try:
            return get() if get else ""
        except Exception:
            return ""

    def _commit_editor(self):
        if self.editor is None:
            return
        entry = self.editor_entry
        new_para_text = self.editor.toPlainText()
        key = entry["area"]
        paras = (self._area_text(key) or "").split("\n")
        while len(paras) <= entry["para"]:
            paras.append("")
        paras[entry["para"]] = new_para_text
        new_text = "\n".join(paras)
        w = self._field_widget(key)
        try:
            if hasattr(w, "setPlainText"):
                w.setPlainText(new_text)
            else:
                w.setText(new_text)
        except Exception:
            pass
        self._close_editor(commit=False)
        try:
            self.win.toast("Line updated - re-rendering page...")
            self.generate()
        except (RuntimeError, AttributeError):
            pass  # shutting down; nothing to re-render into

    def _close_editor(self, commit):
        if self.editor is None:
            return
        if commit:
            self._commit_editor()
            return
        try:
            self.editor.deleteLater()
        except Exception:
            pass
        self.editor = None

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        try:
            return self._filtered_event(obj, event)
        except RuntimeError:
            return False  # widgets torn down during shutdown

    def _filtered_event(self, obj, event):
        from PySide6.QtCore import QEvent
        if getattr(self, "preview_scroll", None) is None:
            return super().eventFilter(obj, event)
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
        elif obj is self.view and self.pages:
            if event.type() == QEvent.MouseMove and self.editor is None:
                self._show_hover(self._line_at(
                    self._page_point(event.position().toPoint())))
            elif event.type() == QEvent.Leave and self.editor is None:
                self._show_hover(None)
            elif event.type() == QEvent.MouseButtonPress and \
                    event.button() == Qt.LeftButton and self.editor is None:
                entry = self._line_at(
                    self._page_point(event.position().toPoint()))
                if entry is not None:
                    self._open_editor(entry)
                    return True
        elif obj is self.editor and self.editor is not None:
            if event.type() == QEvent.KeyPress:
                if event.key() in (Qt.Key_Return, Qt.Key_Enter) and \
                        event.modifiers() & Qt.ControlModifier:
                    self._close_editor(commit=True)
                    return True
                if event.key() == Qt.Key_Escape:
                    self.editor_cancelled = True
                    self._close_editor(commit=False)
                    return True
            elif event.type() == QEvent.FocusOut:
                if not getattr(self, "editor_cancelled", False):
                    self._close_editor(commit=True)
                    return True
        return super().eventFilter(obj, event)

    def refresh(self):
        self.reload_options()
