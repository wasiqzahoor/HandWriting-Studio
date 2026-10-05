"""Stroke model placeholder (spec section 4: Stroke Model slot).

Today: subtle per-glyph ink-density/edge treatment driven by the variation
engine (alpha jitter applied in the renderer). The interface below is what a
future real stroke engine (pressure/velocity/texture synthesis) will
implement - the renderer already calls through it, so swapping technology
requires no UI or document changes.
"""
from PIL import Image, ImageEnhance


class StrokeEngine:
    kind = "placeholder"

    def __init__(self, strength: float = 1.0):
        self.strength = max(0.0, min(1.5, strength))

    def process(self, glyph: Image.Image, alpha: float) -> Image.Image:
        """Apply stroke character. Currently: contrast/ink jitter only."""
        if abs(self.strength - 1.0) < 1e-6 and alpha >= 0.999:
            return glyph
        # Honest placeholder: slight contrast shift proportional to strength.
        enhancer = ImageEnhance.Contrast(glyph)
        factor = 1.0 + 0.06 * (self.strength - 1.0)
        return enhancer.enhance(max(0.5, factor))
