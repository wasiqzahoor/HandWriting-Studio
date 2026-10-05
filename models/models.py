"""Internal data models (spec section 43). UI-independent dataclasses."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RenderingSettings:
    font_size: int = 42
    spacing: int = 2
    slant: float = 0.08
    variation: float = 0.6
    seed: int = 12345
    baseline_jitter: float = 1.0   # multiplier 0..1.5 (advanced)
    stroke_jitter: float = 1.0     # multiplier 0..1.5 (advanced)

    def to_dict(self) -> dict:
        return {"font_size": self.font_size, "spacing": self.spacing,
                "slant": self.slant, "variation": self.variation,
                "seed": self.seed, "baseline_jitter": self.baseline_jitter,
                "stroke_jitter": self.stroke_jitter}

    @classmethod
    def from_dict(cls, d: dict) -> "RenderingSettings":
        kw = {k: d[k] for k in
              ("font_size", "spacing", "slant", "variation", "seed",
               "baseline_jitter", "stroke_jitter") if k in d}
        return cls(**kw)


@dataclass
class ProfileMeta:
    profile_id: str
    name: str
    author: str = ""
    version: str = "1.0"
    renderer: str = "glyph_based"
    description: str = ""
    supported_chars: List[str] = field(default_factory=list)
    is_default: bool = False
    path: str = ""


@dataclass
class TemplateSpec:
    template_id: str
    name: str
    kind: str = "card"          # card | envelope
    width_in: float = 4.0
    height_in: float = 6.0
    dpi: int = 300
    margins_in: Dict[str, float] = field(
        default_factory=lambda: {"top": 0.35, "left": 0.35,
                                 "right": 0.35, "bottom": 0.35})
    fields: List[str] = field(default_factory=lambda: ["header", "body"])
    is_default: bool = False
    builtin: bool = True


@dataclass
class BatchRecord:
    index: int
    data: Dict[str, str]
    status: str = "pending"     # pending|success|failed|skipped
    error: str = ""
    outputs: List[str] = field(default_factory=list)


@dataclass
class ExportRecord:
    filename: str
    doc_type: str
    template: str
    profile: str
    created: str
    format: str
    status: str
    location: str
