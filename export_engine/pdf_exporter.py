"""PDF export: exact physical page, full-bleed image, no scaling (spec 36)."""
import os
import tempfile

from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader
from document_engine.dimensions import Units


def export_pdf(pil_image, path, width_in, height_in, title="Handwriting Studio"):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    w_pt, h_pt = Units.page_pt(width_in, height_in)
    c = rl_canvas.Canvas(path, pagesize=(w_pt, h_pt))
    c.setTitle(title)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        from PIL import Image as _I
        img = pil_image
        if img.mode == "RGBA":
            bg = _I.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        img.save(tmp_path, "PNG", dpi=(300, 300))
        c.drawImage(ImageReader(tmp_path), 0, 0, width=w_pt, height=h_pt,
                    preserveAspectRatio=False, anchor="c")
        c.showPage()
        c.save()
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
    return path
