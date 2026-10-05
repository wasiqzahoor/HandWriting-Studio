"""Image export: PNG (JPEG later). Preserves pixels + DPI (spec 35)."""
import os
from PIL import Image


def export_png(image, path, dpi=300):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    img = image
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, (253, 252, 247))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    img.save(path, "PNG", dpi=(dpi, dpi))
    return path


def export_jpeg(image, path, dpi=300, quality=92):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    img = image.convert("RGB") if image.mode != "RGB" else image
    img.save(path, "JPEG", dpi=(dpi, dpi), quality=quality)
    return path
