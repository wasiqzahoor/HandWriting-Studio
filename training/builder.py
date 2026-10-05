"""Profile builder: sample + base font + coverage -> portable profile.

Honest pipeline (spec 62): glyphs are rendered from a handwriting base font
tinted with the SAMPLE-DERIVED ink, for exactly the user-confirmed
character set, with seeded variants. This is labelled everywhere as a
glyph-built profile - not a trained neural model. The training/ package
already outputs the portable profile layout so a future real extractor can
drop glyphs/variants/model in without app changes.
"""
import json
import os
import random

from PIL import ImageFont

PRINTABLE = [chr(c) for c in range(32, 127) if chr(c) not in ("\t",)]


def build_profile(dest_dir, name, author, base_font, ink, charset,
                  variants=3, seed=7):
    """charset: iterable of single chars. Returns (supported, skipped)."""
    os.makedirs(os.path.join(dest_dir, "glyphs"), exist_ok=True)
    try:
        font = ImageFont.truetype(base_font, 64)
        ascent, descent = font.getmetrics()
    except Exception:
        font = ImageFont.load_default()
        ascent, descent = 52, 14
    from PIL import Image, ImageDraw
    rng = random.Random(seed)
    supported, skipped = [], []
    for ch in sorted(set(charset)):
        if ch in (" ",):
            supported.append(ch)
            continue
        try:
            l, _t, r, _b = font.getbbox(ch)
            ink_w = max(2, r - l)
        except Exception:
            skipped.append(ch)
            continue
        pad, box_h, baseline = 10, ascent + descent + 20, 10 + ascent
        base = Image.new("RGBA", (ink_w + pad * 2, box_h), (0, 0, 0, 0))
        ImageDraw.Draw(base).text((pad - l, baseline), ch, font=font,
                                  fill=(0, 0, 0, 255), anchor="ls")
        bbox = base.getbbox()
        if not bbox or base.split()[-1].getextrema()[1] < 12:
            skipped.append(ch)
            continue
        x0, _, x1, _ = bbox
        base = base.crop((max(0, x0 - 1), 0,
                          min(base.width, x1 + 1), base.height))
        # base + seeded variants (tiny rotation/scale differences baked in)
        import numpy as np
        arr = np.asarray(base).copy()
        arr[..., 0], arr[..., 1], arr[..., 2] = ink
        base_inked = Image.fromarray(arr, "RGBA")
        base_inked.save(os.path.join(dest_dir, "glyphs",
                                     f"U+{ord(ch):04X}.png"))
        n_var = 0
        for v in range(1, variants):
            ang = rng.uniform(-1.5, 1.5)
            sc = rng.uniform(0.97, 1.03)
            var = base_inked.rotate(ang, expand=True,
                                    resample=Image.BICUBIC)
            nw = max(2, int(var.width * sc))
            nh = max(2, int(var.height * sc))
            var = var.resize((nw, nh), Image.BICUBIC)
            var.save(os.path.join(dest_dir, "glyphs",
                                  f"U+{ord(ch):04X}_v{v}.png"))
            n_var += 1
        supported.append(ch)
    meta = {"name": name, "author": author, "version": "1.0",
            "renderer": "glyph_based",
            "description": f"Glyph-built profile from samples ({len(supported)}"
                           f" chars, {variants} variants). Builder output - "
                           "not a trained neural model."}
    cfg = {"base_font": base_font, "ink": list(ink),
           "default_size_px": 42, "spacing_px": 2, "slant": 0.08,
           "builder": "training.builder v1", "seed": seed}
    with open(os.path.join(dest_dir, "metadata.json"), "w",
              encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    with open(os.path.join(dest_dir, "configuration.json"), "w",
              encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    return supported, skipped
