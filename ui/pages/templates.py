"""Templates page (spec 19-21): cards with live thumbnails + CRUD."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QDialog, QFormLayout, QLineEdit,
                               QComboBox, QDoubleSpinBox, QDialogButtonBox,
                               QMessageBox, QScrollArea, QFrame, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PIL import Image, ImageDraw

from ui.components import (PageHeader, Card, primary_button, ghost_button,
                           danger_button)
from template_engine.templates import Template


def thumbnail(template, w=300):
    u_w, u_h = template.canvas_px
    scale = w / u_w
    h = max(120, int(u_h * scale))
    bg = (255, 255, 255) if template.page_white else (253, 252, 247)
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    geo = template.geometry()
    if template.ruled:
        yy = 20.0
        while yy < h - 6:
            d.line([(8, yy), (w - 8, yy)], fill=(170, 190, 210), width=1)
            yy += template.base_font_size * 1.9 * scale
    for key, x, y, ww, hh, _fs, _head in geo["areas"]:
        d.rectangle([x * scale, y * scale, (x + ww) * scale,
                     (y + hh) * scale], outline=(200, 60, 70), width=2)
        d.text((x * scale + 6, y * scale + 4), key.upper(), fill=(150, 150, 155))
    if template.kind == "envelope" and "stamp_box" in geo:
        sx, sy, sw, sh = geo["stamp_box"]
        d.rectangle([sx * scale, sy * scale, (sx + sw) * scale,
                     (sy + sh) * scale], outline=(42, 157, 143), width=2)
        d.text((sx * scale + 6, sy * scale + 4), "STAMP",
               fill=(42, 157, 143))
    from PIL.ImageQt import ImageQt
    return QPixmap.fromImage(ImageQt(img))


class TemplateDialog(QDialog):
    def __init__(self, parent, template=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Template" if template else "New Template")
        self.setMinimumWidth(380)
        f = QFormLayout(self)
        self.name = QLineEdit(template.name if template else "")
        self.kind = QComboBox()
        self.kind.addItems(["card", "envelope"])
        if template:
            self.kind.setCurrentText(template.kind)
        self.w = QDoubleSpinBox()
        self.w.setRange(1, 20)
        self.w.setValue(template.width_in if template else 4.0)
        self.h = QDoubleSpinBox()
        self.h.setRange(1, 20)
        self.h.setValue(template.height_in if template else 6.0)
        self.mt = QDoubleSpinBox()
        self.mt.setRange(0, 2)
        self.mt.setSingleStep(0.05)
        self.mt.setValue((template.margins_in if template else {}).get(
            "top", 0.35))
        self.fs = QDoubleSpinBox()
        self.fs.setRange(12, 96)
        self.fs.setValue(template.base_font_size if template else 42)
        from PySide6.QtWidgets import QCheckBox
        self.ck_ruled = QCheckBox("Ruled lines")
        self.ck_ruled.setChecked(template.ruled if template else False)
        self.ck_white = QCheckBox("White page")
        self.ck_white.setChecked(template.page_white if template else False)
        f.addRow("Name:", self.name)
        f.addRow("Kind:", self.kind)
        f.addRow("Width (in):", self.w)
        f.addRow("Height (in):", self.h)
        f.addRow("Margin (in):", self.mt)
        f.addRow("Base font size:", self.fs)
        f.addRow("Lines:", self.ck_ruled)
        f.addRow("Paper:", self.ck_white)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addWidget(bb)

    def result_template(self, template_id, builtin=False):
        m = self.mt.value()
        return Template(template_id, self.name.text().strip() or template_id,
                        self.kind.currentText(), self.w.value(),
                        self.h.value(),
                        {"top": m, "left": m, "right": m, "bottom": m},
                        ("sender", "recipient")
                        if self.kind.currentText() == "envelope"
                        else ("header", "body"), builtin, False, self.fs.value(),
                        self.ck_white.isChecked(), self.ck_ruled.isChecked())


class TemplatesPage(QWidget):
    def __init__(self, ctx, win):
        super().__init__()
        self.ctx = ctx
        self.win = win
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)
        head = PageHeader("Templates", "4\u00d76 cards and #10 envelopes. "
                                      "Dimensions stay physically accurate.")
        new_btn = primary_button("+ New Template")
        new_btn.clicked.connect(self.create)
        head.add_action(new_btn)
        root.addWidget(head)

        sc = QScrollArea()
        sc.setWidgetResizable(True)
        self.wrap = QWidget()
        self.wrap.setObjectName("scrollbody")
        self.grid = QGridLayout(self.wrap)
        self.grid.setSpacing(12)
        sc.setWidget(self.wrap)
        root.addWidget(sc, 1)
        self.refresh()

    def refresh(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, t in enumerate(self.ctx.templates.list()):
            self.grid.addWidget(self._card(t), i, 0)

    def _card(self, t):
        c = Card()
        outer = QHBoxLayout()
        outer.setSpacing(16)
        thumb = QLabel()
        thumb.setAlignment(Qt.AlignCenter)
        thumb.setFixedWidth(220)
        thumb.setPixmap(thumbnail(t, w=220))
        outer.addWidget(thumb)
        info = QVBoxLayout()
        info.setSpacing(8)
        title = QLabel(t.name)
        title.setStyleSheet("font-weight: 800; font-size: 15px;")
        info.addWidget(title)
        kind = QLabel(f"{t.kind.upper()}  \u00b7  {t.width_in} x "
                      f"{t.height_in} in  \u00b7  fields: "
                      f"{', '.join(t.fields)}"
                      f"{'  \u00b7  RULED' if t.ruled else ''}"
                      f"{'  \u00b7  WHITE' if t.page_white else ''}"
                      f"{'  \u00b7  DEFAULT' if t.is_default else ''}"
                      f"{'  \u00b7  built-in' if t.builtin else ''}")
        kind.setProperty("class", "muted")
        kind.setWordWrap(True)
        kind.setMinimumWidth(20)
        info.addWidget(kind)
        info.addStretch(1)
        row = QHBoxLayout()
        row.setSpacing(8)
        use = primary_button("Use")
        use.clicked.connect(lambda _=False, tid=t.template_id:
                            self.win.pages[1].use_template(tid))
        edit = ghost_button("Edit")
        edit.clicked.connect(lambda _=False, tt=t: self.edit(tt))
        dup = ghost_button("Duplicate")
        dup.clicked.connect(lambda _=False, tt=t: self.duplicate(tt))
        dflt = ghost_button("Set Default")
        dflt.clicked.connect(lambda _=False, tid=t.template_id:
                             self._default(tid))
        for b in (use, edit, dup, dflt):
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            row.addWidget(b, 1)
        if not t.builtin:
            dele = danger_button("Delete")
            dele.clicked.connect(lambda _=False, tid=t.template_id:
                                 self._delete(tid))
            dele.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            row.addWidget(dele, 1)
        info.addLayout(row)
        outer.addLayout(info, 1)
        c.layout().addLayout(outer)
        return c

    def create(self):
        dlg = TemplateDialog(self)
        if dlg.exec():
            base = "".join(c if c.isalnum() else "-" for c in
                           dlg.name.text().lower()).strip("-") or "custom"
            tid = base
            n = 2
            ids = {t.template_id for t in self.ctx.templates.list()}
            while tid in ids:
                tid = f"{base}-{n}"
                n += 1
            self.ctx.templates.save_custom(dlg.result_template(tid))
            self.refresh()
            self.win.toast("Template created.")

    def edit(self, t):
        if t.builtin:
            self.win.toast("Built-in templates: margins/size can be tuned via "
                           "Duplicate to keep the original intact.", "warn")
            return
        dlg = TemplateDialog(self, t)
        if dlg.exec():
            nt = dlg.result_template(t.template_id)
            nt.is_default = t.is_default
            self.ctx.templates.save_custom(nt)
            self.refresh()
            self.win.toast("Template updated.")

    def duplicate(self, t):
        ids = {x.template_id for x in self.ctx.templates.list()}
        nid, n = f"{t.template_id}-copy", 2
        while nid in ids:
            nid = f"{t.template_id}-copy-{n}"
            n += 1
        self.ctx.templates.duplicate(t.template_id, nid, f"{t.name} (copy)")
        self.refresh()
        self.win.toast("Template duplicated.")

    def _default(self, tid):
        self.ctx.templates.set_default(tid)
        self.ctx.settings.set("default_template", tid)
        self.refresh()
        self.win.toast("Default template updated.")

    def _delete(self, tid):
        if QMessageBox.question(
                self, "Delete template",
                "Delete this custom template?") == QMessageBox.Yes:
            try:
                self.ctx.templates.delete(tid)
                self.refresh()
                self.win.toast("Template deleted.")
            except Exception as e:
                self.win.toast(str(e), "error")
