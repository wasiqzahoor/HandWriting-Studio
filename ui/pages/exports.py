"""Exports history (spec 29): filename/type/template/profile/date/status."""
import datetime
import os
import subprocess
import sys as _sys

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QMessageBox, QLineEdit)
from ui.components import (PageHeader, Card, ghost_button, danger_button,
                           make_table, set_table_rows, EmptyState)


class ExportsPage(QWidget):
    def __init__(self, ctx, win):
        super().__init__()
        self.ctx = ctx
        self.win = win
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)
        head = PageHeader("Exports", "Every file this app has produced.")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter by filename...")
        self.search.setMaximumWidth(260)
        self.search.textChanged.connect(lambda: self.refresh())
        head.add_action(self.search)
        root.addWidget(head)

        card = Card()
        self.empty = EmptyState("No exports yet",
                                "Generate a document or run a batch job.")
        card.layout().addWidget(self.empty)
        self.table = make_table(["File", "Type", "Template", "Profile",
                                 "Date", "Format", "Status", "ID"])
        self.table.setColumnHidden(7, True)
        self.table.setMinimumHeight(320)
        card.layout().addWidget(self.table)
        root.addWidget(card, 1)

        row = QHBoxLayout()
        row.setSpacing(8)
        b_open = ghost_button("Open")
        b_open.clicked.connect(self.open_sel)
        b_show = ghost_button("Show in Folder")
        b_show.clicked.connect(self.show_sel)
        b_copy = ghost_button("Export Again (copy)")
        b_copy.clicked.connect(self.again)
        b_del = danger_button("Delete Record")
        b_del.clicked.connect(self.delete)
        for b in (b_open, b_show, b_copy, b_del):
            row.addWidget(b)
        row.addStretch(1)
        root.addLayout(row)
        self.refresh()

    def rows(self):
        q = self.search.text().strip().lower()
        out = []
        for r in self.ctx.db.exports():
            if q and q not in r["filename"].lower():
                continue
            out.append(((r["filename"], r["doc_type"], r["template"],
                         r["profile"],
                         datetime.datetime.fromtimestamp(
                             r["created"]).strftime("%Y-%m-%d %H:%M"),
                         r["format"], r["status"], r["id"]), r["location"]))
        return out

    def refresh(self):
        data = self.rows()
        self.empty.setVisible(not data)
        self.table.setVisible(bool(data))
        set_table_rows(self.table, [d[0] for d in data])
        self._locs = [d[1] for d in data]

    def selected(self):
        r = self.table.currentRow()
        if r < 0 or r >= len(self._locs):
            return None, None
        row = self.rows()[r]
        return row[0][7], row[1]

    def open_sel(self):
        _id, loc = self.selected()
        if not loc:
            return
        try:
            if _sys.platform == "win32":
                os.startfile(loc)
            elif _sys.platform == "darwin":
                subprocess.Popen(["open", loc])
            else:
                subprocess.Popen(["xdg-open", loc])
        except Exception as e:
            self.win.toast(f"Cannot open file: {e}", "error")

    def show_sel(self):
        _id, loc = self.selected()
        if not loc:
            return
        folder = os.path.dirname(loc)
        try:
            if _sys.platform == "win32":
                subprocess.Popen(["explorer", "/select,", loc])
            elif _sys.platform == "darwin":
                subprocess.Popen(["open", "-R", loc])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            self.win.toast(f"Cannot reveal file: {e}", "error")

    def again(self):
        _id, loc = self.selected()
        if not loc or not os.path.isfile(loc):
            self.win.toast("Original file is missing.", "error")
            return
        base, ext = os.path.splitext(os.path.basename(loc))
        dest = os.path.join(
            os.path.dirname(loc),
            f"{base}_copy{datetime.datetime.now():%Y%m%d-%H%M%S}{ext}")
        try:
            import shutil
            shutil.copyfile(loc, dest)
            r = [x for x in self.ctx.db.exports() if x["id"] == _id][0]
            self.ctx.db.add_export(os.path.basename(dest), r["doc_type"],
                                   r["template"], r["profile"], r["format"],
                                   "done", dest)
            self.refresh()
            self.win.toast(f"Saved: {os.path.basename(dest)}")
        except Exception as e:
            self.win.toast(f"Copy failed: {e}", "error")

    def delete(self):
        _id, loc = self.selected()
        if _id is None:
            return
        if QMessageBox.question(
                self, "Delete record",
                "Delete this export record (file stays on disk)?"
                ) == QMessageBox.Yes:
            self.ctx.db.delete_export(_id)
            self.refresh()
            self.win.toast("Record deleted.")
