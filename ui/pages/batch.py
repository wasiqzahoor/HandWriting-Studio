"""Batch page (spec 26-28): CSV/TXT import, mapping, progress, errors."""
import csv
import datetime
import os

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QComboBox, QCheckBox, QLineEdit, QFileDialog,
                               QProgressBar, QSplitter, QMessageBox,
                               QScrollArea, QGridLayout, QSizePolicy,
                               QHeaderView)
from PySide6.QtCore import Qt

from ui.components import (PageHeader, Card, primary_button, export_button,
                           ghost_button, danger_button, make_table,
                           set_table_rows, EmptyState)
from batch_engine.sources import load_source
from batch_engine.processor import BatchProcessor


def _clear_layout(lay):
    while lay.count():
        item = lay.takeAt(0)
        if item.widget() is not None:
            item.widget().deleteLater()
        elif item.layout() is not None:
            _clear_layout(item.layout())


class BatchPage(QWidget):
    def __init__(self, ctx, win):
        super().__init__()
        self.ctx = ctx
        self.win = win
        self.columns = []
        self.rows = []
        self.source_path = ""
        self.job_id = None
        self.processor = None

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)
        head = PageHeader("Batch Processing",
                          "Import CSV/TXT, map fields, render every record.")
        root.addWidget(head)

        split = QSplitter(Qt.Horizontal)
        root.addWidget(split, 1)

        # ---- setup ----
        setup = Card()
        sl = setup.layout()
        sl.setSpacing(8)
        sl.addWidget(self._step("1", "Source file"))
        row = QHBoxLayout()
        row.setSpacing(8)
        self.ed_source = QLineEdit()
        self.ed_source.setReadOnly(True)
        self.ed_source.setPlaceholderText("No file selected")
        self.ed_source.setToolTip("CSV or TXT file. CSV needs a header row.")
        pick = ghost_button("Browse...")
        pick.setToolTip("Select a CSV or TXT source file")
        pick.clicked.connect(self.pick_source)
        row.addWidget(self.ed_source, 1)
        row.addWidget(pick)
        sl.addLayout(row)
        txt_lbl = QLabel("TXT mode")
        txt_lbl.setProperty("class", "muted")
        sl.addWidget(txt_lbl)
        self.cmb_txtmode = QComboBox()
        self.cmb_txtmode.addItems(["line", "block"])
        self.cmb_txtmode.setToolTip("line = one document per line, "
                                    "block = split on blank lines")
        sl.addWidget(self.cmb_txtmode)
        sl.addWidget(self._step("2", "Field mapping"))
        self.map_box = QVBoxLayout()
        self.map_box.setSpacing(6)
        sl.addLayout(self.map_box)
        self.map_combos = {}
        self.lbl_nomap = QLabel("Load a source file to map template fields.")
        self.lbl_nomap.setProperty("class", "hint")
        self.lbl_nomap.setWordWrap(True)
        self.lbl_nomap.setMinimumWidth(20)
        self.map_box.addWidget(self.lbl_nomap)
        sl.addWidget(self._step("3", "Template, profile, formats"))
        self.cmb_template = QComboBox()
        self.cmb_template.setToolTip("Document template for every record")
        self.cmb_profile = QComboBox()
        self.cmb_profile.setToolTip("Handwriting profile for every record")
        sl.addWidget(self.cmb_template)
        sl.addWidget(self.cmb_profile)
        fmt = QHBoxLayout()
        fmt.setSpacing(14)
        self.ck_pdf = QCheckBox("PDF")
        self.ck_pdf.setChecked(True)
        self.ck_png = QCheckBox("PNG")
        self.ck_png.setChecked(True)
        fmt.addWidget(self.ck_pdf)
        fmt.addWidget(self.ck_png)
        fmt.addStretch(1)
        sl.addLayout(fmt)
        out = QHBoxLayout()
        out.setSpacing(8)
        self.ed_out = QLineEdit()
        self.ed_out.setReadOnly(True)
        self.ed_out.setPlaceholderText("Default exports folder")
        ob = ghost_button("Browse...")
        ob.setToolTip("Where rendered files are saved")
        ob.clicked.connect(self.pick_out)
        out.addWidget(self.ed_out, 1)
        out.addWidget(ob)
        sl.addLayout(out)
        sl.addSpacing(4)
        grid = QGridLayout()
        grid.setSpacing(8)
        self.btn_start = primary_button("Start")
        self.btn_start.setMinimumHeight(44)
        self.btn_start.setToolTip("Render every record (Ctrl+B)")
        self.btn_start.setShortcut("Ctrl+B")
        self.btn_start.clicked.connect(self.start)
        self.btn_pause = ghost_button("Pause")
        self.btn_pause.setCheckable(True)
        self.btn_pause.setToolTip("Pause / resume the running job")
        self.btn_pause.clicked.connect(
            lambda: self.processor.pause(self.btn_pause.isChecked())
            if self.processor else None)
        self.btn_cancel = danger_button("Cancel")
        self.btn_cancel.setToolTip("Stop the running job")
        self.btn_cancel.clicked.connect(
            lambda: self.processor.cancel() if self.processor else None)
        self.btn_retry = ghost_button("Retry failed")
        self.btn_retry.setToolTip("Re-run only the failed records")
        self.btn_retry.clicked.connect(self.retry)
        self.btn_errors = ghost_button("Error report")
        self.btn_errors.setToolTip("Save failed records as CSV")
        self.btn_errors.clicked.connect(self.error_report)
        self.btn_open = ghost_button("Open output folder")
        self.btn_open.setToolTip("Show rendered files in file manager")
        self.btn_open.clicked.connect(self.open_out)
        for b in (self.btn_start, self.btn_pause, self.btn_cancel,
                  self.btn_retry, self.btn_errors, self.btn_open):
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.setMinimumHeight(38)
        grid.addWidget(self.btn_start, 0, 0, 1, 2)
        grid.addWidget(self.btn_pause, 1, 0)
        grid.addWidget(self.btn_cancel, 1, 1)
        grid.addWidget(self.btn_retry, 2, 0)
        grid.addWidget(self.btn_errors, 2, 1)
        grid.addWidget(self.btn_open, 3, 0, 1, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        sl.addLayout(grid)
        sl.addStretch(1)
        setup_scroll = QScrollArea()
        setup_scroll.setWidgetResizable(True)
        setup_scroll.setWidget(setup)
        setup_scroll.setMinimumWidth(400)
        split.addWidget(setup_scroll)

        # ---- progress + records ----
        right = Card()
        rl = right.layout()
        self.lbl_job = QLabel("No batch job yet.")
        self.lbl_job.setStyleSheet("font-weight: 800; font-size: 14px;")
        rl.addWidget(self.lbl_job)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        rl.addWidget(self.bar)
        self.lbl_counts = QLabel("Total: 0  \u00b7  Processed: 0  \u00b7  "
                                 "Successful: 0  \u00b7  Failed: 0  \u00b7  "
                                 "Remaining: 0")
        self.lbl_counts.setProperty("class", "muted")
        self.lbl_counts.setWordWrap(True)
        self.lbl_counts.setMinimumWidth(20)
        rl.addWidget(self.lbl_counts)
        self.empty = EmptyState("Nothing here yet",
                                "Select a CSV/TXT source on the left, map "
                                "the fields, then press Start.")
        rl.addWidget(self.empty, 1)
        self.table = make_table(["#", "Preview", "Status", "Message"])
        self.table.setMinimumHeight(260)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.Stretch)
        rl.addWidget(self.table, 1)
        self.table.setVisible(False)
        split.addWidget(right)
        split.setSizes([440, 600])
        split.setStretchFactor(1, 1)
        self.cmb_template.currentIndexChanged.connect(
            self.pick_refresh_mapping)
        self.reload_options()

    @staticmethod
    def _step(num, title):
        lab = QLabel(f'<span style="color:#E63946;font-weight:800;">'
                     f'{num}.</span> <b>{title}</b>')
        lab.setStyleSheet("font-size: 13px; padding-top: 4px;")
        return lab

    def reload_options(self):
        keep_tpl = self.cmb_template.currentData()
        keep_prof = self.cmb_profile.currentData()
        self.cmb_template.blockSignals(True)
        self.cmb_template.clear()
        for t in self.ctx.templates.list():
            self.cmb_template.addItem(t.name, t.template_id)
        idx = self.cmb_template.findData(keep_tpl)
        self.cmb_template.setCurrentIndex(max(0, idx))
        self.cmb_template.blockSignals(False)
        self.cmb_profile.blockSignals(True)
        self.cmb_profile.clear()
        for p in self.ctx.profiles.list_profiles():
            self.cmb_profile.addItem(p["meta"].get("name", p["id"]), p["id"])
        idx = self.cmb_profile.findData(keep_prof)
        self.cmb_profile.setCurrentIndex(max(0, idx))
        self.cmb_profile.blockSignals(False)

    def refresh(self):
        self.reload_options()

    # ------------------------------------------------------------- source ---
    def pick_source(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV or TXT", "", "Data (*.csv *.txt)")
        if not path:
            return
        try:
            cols, rows = load_source(path, self.cmb_txtmode.currentText())
        except Exception as e:
            self.win.toast(f"Cannot load source: {e}", "error")
            return
        self.columns, self.source_path = cols, path
        self.rows = [{"idx": i, "data": r} for i, r in enumerate(rows)]
        self.ed_source.setText(f"{os.path.basename(path)} ({len(rows)} records)")
        self._build_mapping()
        set_table_rows(self.table, [(r["idx"] + 1,
                                     str(list(r["data"].values())[0])[:60],
                                     "pending", "") for r in self.rows[:200]])
        self.empty.setVisible(False)
        self.table.setVisible(True)
        self.win.toast(f"Loaded {len(rows)} records.")

    def _build_mapping(self):
        if not self.columns:
            return
        self.map_box.removeWidget(self.lbl_nomap)
        self.lbl_nomap.setVisible(False)
        _clear_layout(self.map_box)
        self.map_combos = {}
        tpl = self.ctx.templates.get(self.cmb_template.currentData()
                                     or "four_by_six")
        for field in tpl.fields:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{field} \u2192"))
            cmb = QComboBox()
            cmb.addItems(self.columns)
            # smart default: same-name column, else first
            for i, c in enumerate(self.columns):
                if c.lower() == field.lower() or (
                        field in ("body", "recipient", "text")
                        and c.lower() in ("message", "text", "body",
                                          "recipient", "address")):
                    cmb.setCurrentIndex(i)
                    break
            row.addWidget(cmb, 1)
            self.map_box.addLayout(row)
            self.map_combos[field] = cmb

    def pick_refresh_mapping(self):
        self._build_mapping()

    def pick_out(self):
        d = QFileDialog.getExistingDirectory(self, "Output folder")
        if d:
            self.ed_out.setText(d)

    def mapping(self):
        return {f: c.currentText() for f, c in self.map_combos.items()}

    # --------------------------------------------------------------- run ----
    def start(self, only=()):
        if not self.rows:
            self.win.toast("Select a CSV/TXT source first.", "warn")
            return
        if self.processor and self.processor.isRunning():
            self.win.toast("A job is already running.", "warn")
            return
        formats = ([ "pdf" ] if self.ck_pdf.isChecked() else []) + (
            ["png"] if self.ck_png.isChecked() else [])
        if not formats:
            self.win.toast("Select at least one export format.", "warn")
            return
        tid = self.cmb_template.currentData()
        pid = self.cmb_profile.currentData()
        outdir = self.ed_out.text().strip() or os.path.join(
            self.ctx.paths.exports,
            f"batch_{datetime.datetime.now():%Y%m%d-%H%M%S}")
        os.makedirs(outdir, exist_ok=True)
        st = {"font_size": self.ctx.settings.get("default_font_size", 42),
              "spacing": 0, "slant": 0.08,
              "variation": self.ctx.settings.get("default_variation", 0.6),
              "seed": 1000, "dpi": self.ctx.settings.get("dpi", 300)}
        name = os.path.basename(self.source_path)
        if not only:
            self.job_id = self.ctx.db.create_job(
                name, tid, pid, self.source_path, len(self.rows), outdir)
            self.ctx.db.init_records(self.job_id, len(self.rows))
        self.ctx.db.set_job_status(self.job_id, "running")
        self.lbl_job.setText(f"Batch Job #{self.job_id} - {name}")
        self.processor = BatchProcessor(self.ctx, self.job_id, self.rows,
                                        self.mapping(), tid, pid, st, outdir,
                                        formats, only=only)
        self.processor.progress.connect(self._progress)
        self.processor.record_done.connect(self._record)
        self.processor.finished.connect(self._finished)
        self.processor.failed.connect(
            lambda m: self.win.toast(f"Batch crashed: {m}", "error"))
        self.btn_pause.setChecked(False)
        self.processor.start()
        self.win.toast("Batch job started.")

    def _progress(self, done, total, ok, failed):
        self.bar.setRange(0, max(1, total))
        self.bar.setValue(done)
        self.lbl_counts.setText(
            f"Total: {total}  \u00b7  Processed: {done}  \u00b7  "
            f"Successful: {ok}  \u00b7  Failed: {failed}  \u00b7  "
            f"Remaining: {total - done}")

    def _record(self, idx, success, msg):
        for r in range(self.table.rowCount()):
            if self.table.item(r, 0) and \
                    int(self.table.item(r, 0).text()) == idx + 1:
                from PySide6.QtWidgets import QTableWidgetItem
                self.table.setItem(r, 2, QTableWidgetItem(
                    "success" if success else "failed"))
                self.table.setItem(r, 3, QTableWidgetItem(msg[:120]))
                break

    def _finished(self, job_id):
        job = self.ctx.db.job(job_id)
        if job["failed"]:
            self.win.toast(f"Job done with {job['failed']} errors - "
                           "see records / retry failed.", "warn")
        else:
            self.win.toast("Batch job completed successfully.")
        self.btn_pause.setChecked(False)

    def retry(self):
        if not self.job_id:
            return
        failed = [r["idx"] for r in
                  self.ctx.db.failed_records(self.job_id)]
        if not failed:
            self.win.toast("No failed records to retry.")
            return
        self.start(only=failed)

    def error_report(self):
        if not self.job_id:
            return
        rows = self.ctx.db.failed_records(self.job_id)
        if not rows:
            self.win.toast("No errors in this job.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Error report", f"errors_job{self.job_id}.csv",
            "CSV (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["record", "error", "timestamp"])
            ts = datetime.datetime.now().isoformat(timespec="seconds")
            for r in rows:
                w.writerow([r["idx"] + 1, r["error"], ts])
        self.win.toast(f"Error report saved: {path}")

    def open_out(self):
        import subprocess
        import sys as _sys
        d = self.ed_out.text().strip() or self.ctx.paths.exports
        try:
            if _sys.platform == "win32":
                os.startfile(d)
            elif _sys.platform == "darwin":
                subprocess.Popen(["open", d])
            else:
                subprocess.Popen(["xdg-open", d])
        except Exception as e:
            self.win.toast(f"Cannot open folder: {e}", "error")
