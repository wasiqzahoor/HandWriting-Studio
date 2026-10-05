"""ExportManager: naming, PDF/PNG dispatch, history records (spec 35)."""
import datetime
import os

from export_engine.pdf_exporter import export_pdf
from export_engine.image_exporter import export_png, export_jpeg


class ExportManager:
    def __init__(self, db, default_dir):
        self.db = db
        self.default_dir = default_dir

    def build_name(self, pattern, template_id, profile_id, seed, ext,
                   name="document"):
        date = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        safe = "".join(c if (c.isalnum() or c in "-_") else "_"
                       for c in name)[:40] or "document"
        return (pattern.format(template=template_id, profile=profile_id,
                               seed=seed, date=date, name=safe) + f".{ext}")

    def export(self, image, size_in, outdir, basename, formats,
               doc_type="document", template="", profile=""):
        """formats: subset of ('pdf','png','jpg'). Returns [paths]."""
        os.makedirs(outdir, exist_ok=True)
        w_in, h_in = size_in
        paths = []
        if "pdf" in formats:
            p = os.path.join(outdir, basename + ".pdf")
            export_pdf(image, p, w_in, h_in)
            paths.append(p)
            self.db.add_export(os.path.basename(p), doc_type, template,
                               profile, "pdf", "done", p)
        if "png" in formats:
            p = os.path.join(outdir, basename + ".png")
            export_png(image, p)
            paths.append(p)
            self.db.add_export(os.path.basename(p), doc_type, template,
                               profile, "png", "done", p)
        if "jpg" in formats:
            p = os.path.join(outdir, basename + ".jpg")
            export_jpeg(image, p)
            paths.append(p)
            self.db.add_export(os.path.basename(p), doc_type, template,
                               profile, "jpg", "done", p)
        return paths
