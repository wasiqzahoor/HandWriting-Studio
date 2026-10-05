"""HandwritingEngine facade - the ONLY entry the UI/document layer uses.

    engine.render_document(template, fields, profile_id, settings)
        -> (PIL image, warnings list, info dict)

Owns: profile resolution, seeded RNG stream, word-flow composition, header,
ink-from-sample. Renderers own glyph styling only. Future StrokeRenderer /
NeuralRenderer plug in via _renderers without touching callers.
"""
import random

from handwriting_engine.renderer import GlyphRenderer
from handwriting_engine.stroke_engine import StrokeEngine
from handwriting_engine.layout_engine import (split_paragraphs,
                                              line_height_for)


class HandwritingEngine:
    def __init__(self, profile_manager):
        self.profiles = profile_manager
        self._renderers = {"glyph_based": GlyphRenderer()}
        self.fallback_renderer = "glyph_based"

    def renderer_for(self, profile):
        kind = profile["meta"].get("renderer", "glyph_based")
        return self._renderers.get(kind,
                                  self._renderers[self.fallback_renderer])

    # ------------------------------------------------------------- main ---
    def render_document(self, template, fields, profile_id, settings):
        """template: TemplateSpec-like (geometry in px + areas).
        fields: dict e.g. {"header":..., "body":...} or envelope fields.
        settings: plain dict (font_size/spacing/slant/variation/seed/...).
        """
        profile = self.profiles.get(profile_id)
        renderer = self.renderer_for(profile)
        gm = profile["glyph_manager"]
        gm.fallback_used = set()
        cfg = profile.get("config", {})

        size = int(settings.get("font_size", cfg.get("default_size_px", 42)))
        spacing = int(settings.get("spacing", cfg.get("spacing_px", 2)))
        slant = float(settings.get("slant", cfg.get("slant", 0.08)))
        variation = float(settings.get("variation", 0.6))
        seed = int(settings.get("seed", 12345))
        bl_mul = float(settings.get("baseline_jitter", 1.0))
        st_mul = float(settings.get("stroke_jitter", 1.0))
        sample = settings.get("sample_path")
        if sample:
            try:
                gm.derive_ink_from_sample(sample)
            except Exception:
                pass

        rng = random.Random(seed)
        stroke = StrokeEngine(st_mul)
        W, H = template["canvas_px"]
        canvas = renderer.make_paper(W, H, seed)
        warnings = []

        from PIL import ImageDraw
        draw = ImageDraw.Draw(canvas)
        line_h = line_height_for(size)

        def space_adv():
            j = int(rng.uniform(-1, 2) * variation) if variation else 0
            return gm.measure(" ", size) + spacing + j

        areas = template["areas"]  # list of (key, x, y, w, h, fsize, head?)
        overflow = False

        for key, ax, ay, aw, ah, fsize, is_head in areas:
            text = (fields.get(key) or "")
            if not text.strip():
                continue
            x = ax + (int(rng.uniform(-3, 3) * variation) if variation else 0)
            y = ay
            right = ax + aw
            bottom = ay + ah
            paras = split_paragraphs(text)
            n_paras = len(paras)
            for pi, para in enumerate(paras):
                words = para.split()
                if not words:
                    if any(p.strip() for p in paras[pi + 1:]):
                        y += int(line_h * 0.55)
                    continue
                for wi, word in enumerate(words):
                    items = renderer.style_word(
                        gm, word, fsize, rng, variation, slant, spacing,
                        bl_mul, st_mul, stroke)
                    ww = sum(a for _, _, a, _ in items) + spacing * max(
                        0, len(items) - 1)
                    if x > ax + 2 and x + ww > right:
                        y += int(line_h * (1.0 if not is_head else 0.6))
                        if y + 8 > bottom:
                            if self._has_more(paras, pi, wi):
                                overflow = True
                            break
                        x = ax
                    for g, bo, adv, sp in items:
                        canvas.alpha_composite(g, (int(x), int(y + bo)))
                        x += adv + sp
                    if wi < len(words) - 1:
                        x += space_adv()
                else:
                    if pi < n_paras - 1 and any(
                            p.strip() for p in paras[pi + 1:]):
                        y += line_h
                        if y + 8 > bottom:
                            overflow = True
                            break
                        x = ax
                    continue
                break
            if is_head and text.strip():
                # hand-drawn rule under header block
                ry = min(y + line_h, bottom - 4) + 4
                for xx in range(ax, ax + aw, 8):
                    wob = int(rng.uniform(-1, 1) * variation)
                    draw.line([(xx, ry + wob),
                               (min(xx + 8, ax + aw), ry + wob)],
                              fill=(120, 130, 150, 255), width=2)

        if overflow:
            warnings.append("Text exceeds the available document area.")
        if gm.fallback_used:
            sample_chars = "".join(sorted(gm.fallback_used)[:12])
            warnings.append(
                "Some characters are not available in this handwriting "
                f"profile ({sample_chars}...); fallback rendering was used.")
        info = {"size_px": (W, H), "seed": seed, "ink": gm.ink_color,
                "renderer": renderer.kind, "overflow": overflow,
                "profile": profile_id}
        return canvas, warnings, info

    @staticmethod
    def _has_more(paras, pi, wi):
        if wi < len(paras[pi].split()) - 1:
            return True
        return any(p.strip() for p in paras[pi + 1:])
