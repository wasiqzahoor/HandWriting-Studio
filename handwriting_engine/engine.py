"""HandwritingEngine facade - the ONLY entry the UI/document layer uses.

    engine.render_document(template, fields, profile_id, settings)
        -> (PIL image, warnings list, info dict)          single page
    engine.render_document_paginated(...)
        -> ([PIL images], warnings list, info dict)      multi-page flow

Owns: profile resolution, seeded RNG stream, word-flow composition, header,
ink-from-sample. Renderers own glyph styling only. Future StrokeRenderer /
NeuralRenderer plug in via _renderers without touching callers.
"""
import random

from handwriting_engine.renderer import GlyphRenderer
from handwriting_engine.stroke_engine import StrokeEngine
from handwriting_engine.layout_engine import (split_paragraphs,
                                              line_height_for)

MAX_PAGES = 20


class HandwritingEngine:
    def __init__(self, profile_manager):
        self.profiles = profile_manager
        self._renderers = {"glyph_based": GlyphRenderer()}
        self.fallback_renderer = "glyph_based"

    def renderer_for(self, profile):
        kind = profile["meta"].get("renderer", "glyph_based")
        return self._renderers.get(kind,
                                  self._renderers[self.fallback_renderer])

    # ------------------------------------------------------------- public ---
    def render_document(self, template, fields, profile_id, settings):
        """Single-page render (overflow becomes a warning)."""
        pages, warnings, info = self._compose(template, fields, profile_id,
                                              settings, paginate=False)
        return pages[0], warnings, info

    def render_document_paginated(self, template, fields, profile_id,
                                  settings):
        """Multi-page render: long text flows onto further pages."""
        return self._compose(template, fields, profile_id, settings,
                             paginate=True)

    # ---------------------------------------------------------- internals ---
    def _setup(self, profile_id, settings, sample_path=None):
        profile = self.profiles.get(profile_id)
        renderer = self.renderer_for(profile)
        gm = profile["glyph_manager"]
        gm.fallback_used = set()
        cfg = profile.get("config", {})
        size = int(settings.get("font_size", cfg.get("default_size_px", 42)))
        return {
            "profile": profile, "renderer": renderer, "gm": gm, "cfg": cfg,
            "size": size,
            "spacing": int(settings.get("spacing", cfg.get("spacing_px", 2))),
            "slant": float(settings.get("slant", cfg.get("slant", 0.08))),
            "variation": float(settings.get("variation", 0.6)),
            "seed": int(settings.get("seed", 12345)),
            "bl_mul": float(settings.get("baseline_jitter", 1.0)),
            "st_mul": float(settings.get("stroke_jitter", 1.0)),
            "rng": random.Random(int(settings.get("seed", 12345))),
            "stroke": StrokeEngine(float(settings.get("stroke_jitter", 1.0))),
        }

    def _compose(self, template, fields, profile_id, settings, paginate):
        st = self._setup(profile_id, settings)
        gm, rng = st["gm"], st["rng"]
        sample = settings.get("sample_path")
        if sample:
            try:
                gm.derive_ink_from_sample(sample)
            except Exception:
                pass
        ink_override = settings.get("ink")
        if ink_override:
            try:
                gm.ink_color = (int(ink_override[0]), int(ink_override[1]),
                                int(ink_override[2]))
            except Exception:
                pass
        renderer = st["renderer"]
        W, H = template["canvas_px"]
        line_h = line_height_for(st["size"])
        page_bg = tuple(template.get("page_bg", (253, 252, 247)))
        if settings.get("page_white") is True:
            page_bg = (255, 255, 255)
        elif settings.get("page_white") is False:
            page_bg = (253, 252, 247)
        ruled = settings.get("ruled")
        if ruled is None:
            ruled = bool(template.get("ruled", False))
        rule_color = tuple(template.get("rule_color", (150, 175, 200)) + (255,)) \
            if len(tuple(template.get("rule_color", (150, 175, 200)))) == 3 \
            else tuple(template.get("rule_color", (150, 175, 200, 255)))

        def draw_rules(canvas):
            """Notebook lines under every body-area baseline grid."""
            if not ruled:
                return
            from PIL import ImageDraw as _ID
            d = _ID.Draw(canvas)
            for job in jobs:
                if job["head"]:
                    continue
                ax, ay, aw, ah = job["box"]
                try:
                    asc, _d = gm.get_font(job["fsize"]).getmetrics()
                except Exception:
                    asc = job["fsize"]
                first = ay + 10 + asc
                yy = first
                while yy < ay + ah - 4:
                    d.line([(ax, yy), (ax + aw, yy)], fill=rule_color,
                           width=2)
                    yy += line_height_for(job["fsize"])

        jobs = []
        base_fs = max(8, int(template.get("base_font_size",
                                          st["size"]) or st["size"]))
        scale = st["size"] / base_fs
        for (key, ax, ay, aw, ah, fsize, is_head) in template["areas"]:
            text = (fields.get(key) or "")
            paras = split_paragraphs(text) if text.strip() else []
            jobs.append({"key": key, "box": (ax, ay, aw, ah),
                         "fsize": max(6, int(fsize * scale)),
                         "head": bool(is_head), "paras": paras,
                         "cursor": (0, 0), "done": not paras})

        def space_adv():
            j = int(rng.uniform(-1, 2) * st["variation"]) \
                if st["variation"] else 0
            return gm.measure(" ", st["size"]) + st["spacing"] + j

        def style_word(word, fsize):
            return renderer.style_word(
                gm, word, fsize, rng, st["variation"], st["slant"],
                st["spacing"], st["bl_mul"], st["st_mul"], st["stroke"])

        pages, overflow = [], False
        line_map = []  # click-to-edit index: {page, area, para, rect}

        from PIL import ImageDraw
        for page_no in range(MAX_PAGES if paginate else 1):
            canvas = renderer.make_paper(W, H, st["seed"], base=page_bg)
            draw_rules(canvas)  # ruled lines sit under the ink
            draw = ImageDraw.Draw(canvas)
            page_full = False
            for job in jobs:
                if job["done"]:
                    continue
                if job["head"] and page_no > 0:
                    job["done"] = True
                    continue
                ax, ay, aw, ah = job["box"]
                fsize = job["fsize"]
                right, bottom = ax + aw, ay + ah
                x = ax + (int(rng.uniform(-3, 3) * st["variation"])
                          if st["variation"] else 0)
                y = ay
                pi, wi = job["cursor"]
                paras = job["paras"]
                stopped = False
                lx = None  # open visual line: [x0, y_top, para_idx]

                def _begin():
                    nonlocal lx
                    lx = [x, y, pi]

                def _flush(x_end):
                    nonlocal lx
                    if lx is not None and x_end > lx[0] + 4:
                        line_map.append(
                            {"page": page_no, "area": job["key"],
                             "para": lx[2],
                             "rect": (lx[0], lx[1], x_end, lx[1] + line_h)})
                    lx = None

                while pi < len(paras):
                    words = paras[pi].split()
                    if not words:
                        if any(p.strip() for p in paras[pi + 1:]):
                            y += int(line_h * 0.55)
                        pi += 1
                        wi = 0
                        lx = None
                        continue
                    if lx is None:
                        _begin()  # open a new visual line here
                    while wi < len(words):
                        items = style_word(words[wi], fsize)
                        ww = sum(a for _, _, a, _ in items) + st["spacing"] * max(
                            0, len(items) - 1)
                        if x > ax + 2 and x + ww > right:
                            _flush(x)
                            y += int(line_h * (1.0 if not job["head"] else 0.6))
                            if y + 8 > bottom:
                                if job["head"] or not paginate:
                                    if self._job_has_more(paras, pi, wi):
                                        overflow = True
                                    stopped = True
                                else:
                                    page_full = True
                                break
                            x = ax
                            _begin()
                            continue
                        for g, bo, adv, sp in items:
                            canvas.alpha_composite(g, (int(x), int(y + bo)))
                            x += adv + sp
                        wi += 1
                        if wi < len(words):
                            x += space_adv()
                    if stopped or page_full:
                        break
                    if pi < len(paras) - 1 and any(
                            p.strip() for p in paras[pi + 1:]):
                        _flush(x)
                        y += line_h
                        if y + 8 > bottom:
                            if job["head"] or not paginate:
                                overflow = True
                                stopped = True
                                break
                            page_full = True
                            pi += 1
                            wi = 0
                            break
                        x = ax
                        _begin()
                    pi += 1
                    wi = 0
                else:
                    _flush(x)
                    job["done"] = True
                if stopped:
                    job["done"] = True
                    for j2 in jobs:
                        j2["done"] = True
                    break
                if page_full:
                    job["cursor"] = (pi, wi)
                    break
                if job["head"] and job["paras"]:
                    ry = min(y + line_h, bottom - 4) + 4
                    for xx in range(ax, ax + aw, 8):
                        wob = int(rng.uniform(-1, 1) * st["variation"])
                        draw.line([(xx, ry + wob),
                                   (min(xx + 8, ax + aw), ry + wob)],
                                  fill=(120, 130, 150, 255), width=2)
            pages.append(canvas)
            if all(j["done"] for j in jobs):
                break
            if not paginate or overflow:
                break
            if page_no + 1 >= MAX_PAGES:
                if any(not j["done"] for j in jobs):
                    overflow = True
                break

        warnings = []
        if overflow:
            if paginate:
                warnings.append(f"Text needed more than {MAX_PAGES} pages; "
                                "later content was omitted.")
            else:
                warnings.append("Text exceeds the available document area.")
        if gm.fallback_used:
            sample_chars = "".join(sorted(gm.fallback_used)[:12])
            warnings.append(
                "Some characters are not available in this handwriting "
                f"profile ({sample_chars}...); fallback rendering was used.")
        info = {"size_px": (W, H), "seed": st["seed"], "ink": gm.ink_color,
                "renderer": renderer.kind, "overflow": overflow,
                "profile": profile_id, "pages": len(pages), "map": line_map}
        return pages, warnings, info

    @staticmethod
    def _job_has_more(paras, pi, wi):
        if wi < len(paras[pi].split()) - 1:
            return True
        return any(p.strip() for p in paras[pi + 1:])
