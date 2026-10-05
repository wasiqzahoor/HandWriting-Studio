"""Glyph provider: profile glyph PNGs (with variants) + TTF fallback.

Asset layout inside a profile:
    glyphs/U+0041.png        base glyph for "A"
    glyphs/U+0041_v1.png     variant 1 ... _v2, _v3 ...

Fallback chain (spec section 53 - never crash on missing chars):
    profile glyph (random variant) -> profile base font -> system handwriting
    font -> caller gets a `fallback_used` flag for the validation warning.
"""
import glob
import os
import re
from PIL import Image, ImageFont
import numpy as np

DEFAULT_INK = (30, 42, 92)

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\segoesc.ttf",
    r"C:\Windows\Fonts\segoescb.ttf",
    r"C:\Windows\Fonts\segoepr.ttf",
    r"C:\Windows\Fonts\LHANDW.TTF",
    r"C:\Windows\Fonts\BRUSHSCI.TTF",
    "/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf",
    "/System/Library/Fonts/Supplemental/MarkerFelt.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
]

_VARIANT_RE = re.compile(r"^U\+([0-9A-F]{4,6})(?:_v(\d+))?\.png$",
                         re.IGNORECASE)


def find_handwriting_font(explicit=None):
    if explicit and os.path.isfile(explicit):
        return explicit
    for p in FONT_CANDIDATES:
        if os.path.isfile(p):
            return p
    return None


class GlyphManager:
    def __init__(self, glyphs_dir=None, font_path=None,
                 ink_color=DEFAULT_INK):
        self.glyphs_dir = glyphs_dir
        self.font_path = font_path or find_handwriting_font()
        self.ink_color = tuple(ink_color)
        self._fonts = {}
        self._glyphs = {}          # (char, variant) -> image
        self._variants = {}        # char -> sorted [variant_idx]
        self.fallback_used = set()
        if glyphs_dir and os.path.isdir(glyphs_dir):
            for f in glob.glob(os.path.join(glyphs_dir, "*.png")):
                m = _VARIANT_RE.match(os.path.basename(f))
                if not m:
                    continue
                ch = chr(int(m.group(1), 16))
                v = int(m.group(2)) if m.group(2) else 0
                try:
                    img = Image.open(f).convert("RGBA")
                    if img.split()[-1].getextrema()[1] < 12:
                        continue  # blank asset
                    self._glyphs[(ch, v)] = img
                    self._variants.setdefault(ch, []).append(v)
                except Exception:
                    continue
            for ch in self._variants:
                self._variants[ch] = sorted(set(self._variants[ch]))
        # nominal size assets were drawn at
        self.asset_nominal = 64

    @property
    def asset_chars(self):
        return set(self._variants)

    def n_variants(self, char):
        return len(self._variants.get(char, []))

    def get_font(self, size_px):
        size_px = max(8, int(size_px))
        if size_px not in self._fonts:
            try:
                if self.font_path and os.path.isfile(self.font_path):
                    f = ImageFont.truetype(self.font_path, size_px)
                else:
                    f = ImageFont.load_default()
            except Exception:
                f = ImageFont.load_default()
            self._fonts[size_px] = f
        return self._fonts[size_px]

    def measure(self, char, size_px):
        if char == " ":
            return int(size_px * 0.42)
        if char == "\t":
            return int(size_px * 1.2)
        if char in self._variants:
            base = self._glyphs.get((char, 0))
            if base is not None:
                return int(base.width * (size_px / self.asset_nominal))
        font = self.get_font(size_px)
        try:
            return max(4, int(font.getlength(char)) + 1)
        except Exception:
            pass
        try:
            l, _t, r, _b = font.getbbox(char)
            return max(4, int(r - l) + 1)
        except Exception:
            return int(size_px * 0.5)

    def _asset(self, char, variant=0):
        if (char, variant) in self._glyphs:
            return self._glyphs[(char, variant)]
        if char in self._variants:  # fall back to base variant
            return self._glyphs.get((char, self._variants[char][0]))
        return None

    def render_glyph(self, char, size_px, variant=0):
        """Baseline-box glyph (full ascent+descent height, cropped sides)."""
        asset = self._asset(char, variant)
        if asset is not None:
            s = size_px / self.asset_nominal
            return asset.resize((max(2, int(asset.width * s)),
                                 max(2, int(asset.height * s))), Image.BICUBIC)
        self.fallback_used.add(char)
        from PIL import ImageDraw
        font = self.get_font(size_px)
        try:
            ascent, descent = font.getmetrics()
        except Exception:
            ascent, descent = size_px, size_px // 4
        pad = 10
        try:
            l, _t, r, _b = font.getbbox(char)
            ink_w = max(2, r - l)
        except Exception:
            l, ink_w = 0, size_px // 2
        box_h = ascent + descent + pad * 2
        baseline = pad + ascent
        img = Image.new("RGBA", (ink_w + pad * 2, box_h), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((pad - l, baseline), char, font=font,
                                 fill=(0, 0, 0, 255), anchor="ls")
        bbox = img.getbbox()
        if bbox:
            x0, _, x1, _ = bbox
            x0, x1 = max(0, x0 - 1), min(img.width, x1 + 1)
            if x1 > x0:
                img = img.crop((x0, 0, x1, img.height))
        return img

    def tint(self, glyph, alpha_scale=1.0):
        if glyph.mode != "RGBA":
            glyph = glyph.convert("RGBA")
        r, g, b = self.ink_color
        data = np.asarray(glyph).copy()
        data[..., 0] = r
        data[..., 1] = g
        data[..., 2] = b
        data[..., 3] = (data[..., 3].astype(float) * float(alpha_scale)
                        ).clip(0, 255).astype(np.uint8)
        return Image.fromarray(data, "RGBA")

    def derive_ink_from_sample(self, sample_path):
        try:
            img = Image.open(sample_path).convert("RGB")
            img.thumbnail((400, 400))
            arr = np.asarray(img).reshape(-1, 3).astype(np.int32)
            bright = arr.mean(axis=1)
            dark = arr[bright < 140]
            if len(dark) < 50:
                k = max(10, int(len(arr) * 0.02))
                dark = arr[np.argpartition(bright, k)[:k]]
            ink = np.clip(np.median(dark, axis=0) * 0.65, 5, 75).astype(int)
            self.ink_color = (int(ink[0]), int(ink[1]),
                              min(110, int(ink[2]) + 22))
        except Exception:
            pass
        return self.ink_color
