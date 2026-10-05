"""Controlled variation engine (spec section 9).

Subtle, seeded randomness: size/spacing/baseline/rotation/slant/ink/glyph
choice. Magnitudes are deliberately small; advanced multipliers let power
users scale baseline/stroke jitter without touching code.
"""
import random


BASE_RANGES = {
    "scale": 0.05,       # +/-5%
    "rotation": 2.0,     # degrees
    "baseline": 2.0,     # px at ~42px size (scaled by size/42)
    "spacing": ( -1.0, 2.0),
    "alpha": 0.14,       # ink density dip
}


def sample_char(rng: random.Random, variation: float, size_px: int,
                baseline_mul: float = 1.0, stroke_mul: float = 1.0):
    v = max(0.0, min(1.0, variation))
    size_k = max(0.5, size_px / 42.0)
    return {
        "scale": rng.uniform(1 - BASE_RANGES["scale"] * v,
                             1 + BASE_RANGES["scale"] * v) if v else 1.0,
        "rotation": rng.uniform(-BASE_RANGES["rotation"] * v,
                                BASE_RANGES["rotation"] * v) if v else 0.0,
        "baseline": rng.uniform(-BASE_RANGES["baseline"] * v,
                                BASE_RANGES["baseline"] * v) * size_k * baseline_mul
        if v else 0.0,
        "spacing": rng.uniform(BASE_RANGES["spacing"][0] * v,
                               BASE_RANGES["spacing"][1] * v) if v else 0.0,
        "alpha": rng.uniform(max(0.82, 1 - BASE_RANGES["alpha"] * v * stroke_mul),
                             1.0),
    }


def pick_variant(rng: random.Random, n_variants: int) -> int:
    if n_variants <= 1:
        return 0
    return rng.randrange(n_variants)


def apply_slant(img, slant: float):
    from PIL import Image as _PI
    if abs(slant) < 1e-4:
        return img
    w, h = img.size
    pad = int(abs(slant) * h) + 2
    coeffs = (1, -slant, pad, 0, 1, 0)
    return img.transform((w + pad * 2, h), _PI.AFFINE, coeffs,
                         resample=_PI.BICUBIC)
