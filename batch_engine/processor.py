"""BatchProcessor: QThread worker, pause/cancel, per-record errors (26,28,40-41).

Never silently fails: every record ends success/failed/skipped with a
message. Retries re-run only failed records.
"""
import os
import time
import traceback

from PySide6.QtCore import QThread, Signal


class BatchProcessor(QThread):
    progress = Signal(int, int, int, int)  # done, total, ok, failed
    record_done = Signal(int, bool, str)   # idx, success, message
    finished = Signal(int)                 # job_id
    failed = Signal(str)

    def __init__(self, ctx, job_id, records, mapping, template_id,
                 profile_id, settings, outdir, formats, only=()):
        super().__init__()
        self.ctx = ctx
        self.job_id = job_id
        self.records = records
        self.mapping = mapping            # template_field -> source column
        self.template_id = template_id
        self.profile_id = profile_id
        self.settings = dict(settings)
        self.outdir = outdir
        self.formats = formats
        self.only = set(only)            # retry subset (empty = all pending)
        self._pause = False
        self._cancel = False

    def pause(self, on=True):
        self._pause = on

    def cancel(self):
        self._cancel = True

    def _wait_if_paused(self):
        while self._pause and not self._cancel:
            time.sleep(0.1)

    def run(self):
        log = self.ctx.log
        try:
            targets = [r for r in self.records
                       if not self.only or r["idx"] in self.only]
            total = len(targets)
            done = ok = failed = 0
            base_seed = int(self.settings.get("seed", 12345))
            for rec in targets:
                if self._cancel:
                    self.ctx.db.set_record(self.job_id, rec["idx"],
                                           "skipped", "cancelled by user")
                    self.record_done.emit(rec["idx"], False, "skipped")
                    done += 1
                    self.progress.emit(done, total, ok, failed)
                    continue
                self._wait_if_paused()
                try:
                    fields = {f: rec["data"].get(col, "")
                              for f, col in self.mapping.items()}
                    st = dict(self.settings)
                    st["seed"] = base_seed + rec["idx"]  # unique yet
                    img, warnings, info = self.ctx.documents.render(
                        self.template_id, fields, self.profile_id, st)
                    stem = f"record_{rec['idx'] + 1:03d}"
                    outs = self.ctx.exports.export(
                        img, info["size_in"], self.outdir, stem,
                        self.formats, doc_type="batch",
                        template=self.template_id, profile=self.profile_id)
                    if warnings:
                        log.warning("record %d warnings: %s",
                                    rec["idx"], warnings)
                    self.ctx.db.set_record(self.job_id, rec["idx"], "success",
                                           "; ".join(warnings),
                                           "\n".join(outs))
                    self.ctx.db.add_document(
                        stem, self.template_id, self.profile_id,
                        st["seed"], "done", outs[0] if outs else "")
                    ok += 1
                    self.record_done.emit(rec["idx"], True, "ok")
                except Exception as e:  # per-record isolation (spec 40)
                    msg = f"{type(e).__name__}: {e}"
                    log.error("record %d failed: %s\n%s", rec["idx"], msg,
                              traceback.format_exc())
                    self.ctx.db.set_record(self.job_id, rec["idx"], "failed",
                                           msg)
                    failed += 1
                    self.record_done.emit(rec["idx"], False, msg)
                done += 1
                self.ctx.db.update_job_counts(
                    self.job_id, done, ok, failed,
                    "cancelled" if self._cancel else "running")
                self.progress.emit(done, total, ok, failed)
            final = "cancelled" if self._cancel else (
                "done" if failed == 0 else "done_with_errors")
            self.ctx.db.set_job_status(self.job_id, final)
            self.finished.emit(self.job_id)
        except Exception as e:
            log.error("batch job %d crashed: %s", self.job_id, e)
            self.failed.emit(str(e))
