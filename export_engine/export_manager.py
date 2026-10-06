"""ExportManager: naming, PDF/PNG dispatch, history records (spec 35)."""
import datetime
import os

from export_engine.pdf_exporter import export_pdf_pages
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

    def export(self, images, size_in, outdir, basename, formats,
               doc_type="document", template="", profile=""):
        """images: one PIL image or list. formats: subset of pdf/png/jpg."""
        if not isinstance(images, (list, tuple)):
            images = [images]
        os.makedirs(outdir, exist_ok=True)
        w_in, h_in = size_in
        multi = len(images) > 1
        paths = []
        if "pdf" in formats:
            p = os.path.join(outdir, basename + ".pdf")
            export_pdf_pages(images, p, w_in, h_in)
            paths.append(p)
            self.db.add_export(os.path.basename(p), doc_type, template,
                               profile, f"pdf/{len(images)}p", "done", p)
        for fmt in ("png", "jpg"):
            if fmt in formats:
                for i, img in enumerate(images):
                    suffix = f"_p{i + 1}" if multi else ""
                    p = os.path.join(outdir, f"{basename}{suffix}.{fmt}")
                    if fmt == "png":
                        export_png(img, p)
                    else:
                        export_jpeg(img, p)
                    paths.append(p)
                    self.db.add_export(
                        os.path.basename(p), doc_type, template, profile,
                        fmt, "done", p)
        return paths
