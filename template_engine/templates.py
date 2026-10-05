"""Template specs: 4x6 card + #10 envelope (spec 20-21).

geometry(dpi) -> {"canvas_px": (W,H), "areas": [(key,x,y,w,h,fsize,is_head)]}.
fsize offsets are per-area (header slightly larger).
"""
from document_engine.dimensions import Units


class Template:
    def __init__(self, template_id, name, kind, width_in, height_in,
                 margins_in=None, fields=("header", "body"), builtin=True,
                 is_default=False, base_font_size=42):
        self.template_id = template_id
        self.name = name
        self.kind = kind
        self.width_in = width_in
        self.height_in = height_in
        self.margins_in = margins_in or {"top": 0.35, "left": 0.35,
                                         "right": 0.35, "bottom": 0.35}
        self.fields = list(fields)
        self.builtin = builtin
        self.is_default = is_default
        self.base_font_size = base_font_size
        self.dpi = 300

    @property
    def canvas_px(self):
        u = Units(self.dpi)
        return (u.in_to_px(self.width_in), u.in_to_px(self.height_in))

    def geometry(self, dpi=300):
        self.dpi = dpi
        u = Units(dpi)
        W, H = self.canvas_px
        m = u.margins_px(self.margins_in)
        cx, cy = m["left"], m["top"]
        cw = W - m["left"] - m["right"]
        if self.kind == "envelope":
            return self._envelope_geometry(cx, cy, cw, W, H, m)
        return self._card_geometry(cx, cy, cw, W, H, m)

    def _card_geometry(self, cx, cy, cw, W, H, m):
        fs = self.base_font_size
        head_h = int(fs * 1.9) + 30
        areas = [("header", cx, cy, cw, head_h, fs + 10, True),
                 ("body", cx, cy + head_h + 30, cw,
                  H - m["bottom"] - (cy + head_h + 30), fs, False)]
        return {"canvas_px": (W, H), "areas": areas}

    def _envelope_geometry(self, cx, cy, cw, W, H, m):
        # #10 envelope: sender top-left, recipient centre, stamp box top-right
        fs = self.base_font_size
        sender_h = int(fs * 1.9) * 3
        stamp_w = u = Units(self.dpi).in_to_px(1.0)
        areas = [
            ("sender", cx, cy, cw - stamp_w - 40, sender_h, fs - 6, False),
            ("recipient", int(W * 0.30), int(H * 0.42), int(W * 0.55),
             int(H * 0.40), fs, False),
        ]
        return {"canvas_px": (W, H), "areas": areas,
                "stamp_box": (W - m["right"] - stamp_w, cy, stamp_w,
                              int(stamp_w * 1.25))}

    def to_dict(self):
        return {"id": self.template_id, "name": self.name, "kind": self.kind,
                "width_in": self.width_in, "height_in": self.height_in,
                "margins_in": self.margins_in, "fields": self.fields,
                "builtin": self.builtin, "is_default": self.is_default,
                "base_font_size": self.base_font_size}

    @classmethod
    def from_dict(cls, d):
        return cls(d["id"], d["name"], d.get("kind", "card"),
                   d["width_in"], d["height_in"], d.get("margins_in"),
                   d.get("fields", ("header", "body")),
                   d.get("builtin", False), d.get("is_default", False),
                   d.get("base_font_size", 42))


def builtin_templates():
    return [
        Template("four_by_six", "4 \u00d7 6 Document", "card", 4.0, 6.0,
                 is_default=True),
        Template("envelope_10", "#10 Envelope", "envelope", 4.125, 9.5,
                 margins_in={"top": 0.4, "left": 0.5,
                             "right": 0.5, "bottom": 0.5},
                 fields=("sender", "recipient")),
    ]
