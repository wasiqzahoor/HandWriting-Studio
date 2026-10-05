"""Renderer abstraction (spec sections 4, 55, 62).

The UI only talks to HandwritingEngine.render(). Concrete technologies
(GlyphRenderer today; StrokeRenderer / NeuralRenderer in the future) plug in
behind this interface without touching UI or document code.

Prototype/placeholder vs production is explicit: every result carries
`renderer_kind` ("glyph_based" today, never advertised as a trained model).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple

from PIL import Image


@dataclass
class RenderResult:
    image: Image.Image
    warning: Optional[str]
    seed: int
    ink: Tuple[int, int, int]
    renderer_kind: str
    overflow: bool = False


class HandwritingRenderer(ABC):
    kind = "base"

    @abstractmethod
    def render(self, text: str, profile: dict, settings: dict) -> RenderResult:
        """Render text with a profile dict + settings dict. Pure function."""
        raise NotImplementedError
