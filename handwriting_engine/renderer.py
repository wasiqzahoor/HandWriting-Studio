"""GlyphRenderer: word-styling primitive (spec 4, 9-11).

Deterministic per seed; controlled variation; multi-variant glyph
selection (spec 10); missing glyphs fall back gracefully and are reported
(spec 53). Page composition lives in engine.py so renderers stay focused.
"""
import random
from PIL import Image

from handwriting_engine.interfaces import HandwritingRenderer, RenderResult
from handwriting_engine.variation_engine import (sample_char, pick_variant,
                                                 apply_slant)
from handwriting_engine.stroke_engine import StrokeEngine


class GlyphRenderer(HandwritingRenderer):
    kind = "glyph_based"

    def __init__(self, paper_color=(253, 252, 247)):
        self.paper_color = paper_color

    def make_paper(self, w, h, seed):
        import numpy as np
        rng = np.random.default_rng(seed)
        base = np.full((h, w, 3), list(self.paper_color[:3]), dtype=np.int16)
        noise = rng.integers(-4, 5, size=(h, w, 1), dtype=np.int16)
        arr = np.clip(base + noise, 0, 255).astype(np.uint8)
        return Image.fromarray(arr, "RGB").convert("RGBA")

    def style_word(self, gm, word, size_px, rng, variation, slant, spacing,
                   bl_mul=1.0, st_mul=1.0, stroke=None):
        """Style one word -> list of (glyph, baseline_off, advance, spacing)."""
        stroke = stroke or StrokeEngine(st_mul)
        items = []
        for ch in word:
            nv = gm.n_variants(ch)
            t = sample_char(rng, variation, size_px, bl_mul, st_mul)
            v = pick_variant(rng, nv) if nv else 0
            g = gm.render_glyph(ch, max(8, int(size_px * t["scale"])),
                                variant=v)
            g = gm.tint(g, t["alpha"])
            g = stroke.process(g, t["alpha"])
            g = apply_slant(g, slant)
            if abs(t["rotation"]) > 0.01:
                g = g.rotate(t["rotation"], expand=True,
                             resample=Image.BICUBIC)
            items.append((g, t["baseline"], g.width + int(t["spacing"]),
                          spacing))
        return items

    # Interface compliance: full-text render on a caller-supplied canvas
    # layout callback. Production path is HandwritingEngine.render_document.
    def render(self, text, profile, settings):
        raise NotImplementedError(
            "Use HandwritingEngine.render_document() - it owns page "
            "composition while this renderer owns glyph styling.")
