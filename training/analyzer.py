"""Sample analysis: honest, offline image metrics (spec 24-25, step 2).

Reports size, ink coverage, estimated ink color, contrast and stroke-width
estimate. No fake OCR: character coverage is confirmed by the user in the
wizard (checkboxes) - the analyzer never pretends to read handwriting.
"""
import os
from PIL import Image
import numpy as np


def analyze_sample(path):
    img = Image.open(path).convert("RGB")
    w, h = img.size
    small = img.copy()
    small.thumbnail((500, 500))
    arr = np.asarray(small).astype(np.int32)
    bright = arr.mean(axis=2)
    ink_mask = bright < 140
    coverage = float(ink_mask.mean())
    contrast = float(bright.max() - bright.min())
    ink = _median_ink(arr, ink_mask)
    stroke = _stroke_estimate(ink_mask)
    return {"path": path, "size": (w, h), "ink_coverage": round(coverage, 4),
            "contrast": round(contrast, 1), "ink": ink,
            "stroke_px": stroke,
            "verdict": _verdict(coverage, contrast, stroke)}


def _median_ink(arr, mask):
    px = arr[mask]
    if len(px) < 50:
        flat = arr.reshape(-1, 3)
        order = flat.mean(axis=1).argsort()[: max(10, len(flat) // 50)]
        px = flat[order]
    med = np.clip(np.median(px, axis=0) * 0.65, 5, 75).astype(int)
    return (int(med[0]), int(med[1]), min(110, int(med[2]) + 22))


def _stroke_estimate(mask):
    # median run-length of ink along rows ~ stroke thickness (rough, honest)
    runs = []
    for row in mask[:: max(1, mask.shape[0] // 60)]:
        n = 0
        for v in row:
            if v:
                n += 1
            elif n:
                runs.append(n)
                n = 0
        if n:
            runs.append(n)
    if not runs:
        return 0.0
    return round(float(np.median(runs)), 1)


def _verdict(coverage, contrast, stroke):
    notes = []
    if coverage < 0.005:
        notes.append("Very little ink - sample may be too faint.")
    if coverage > 0.45:
        notes.append("Very high ink coverage - page may be too dense.")
    if contrast < 60:
        notes.append("Low contrast - clearer photo/scan recommended.")
    if not notes:
        notes.append("Sample looks usable.")
    return " ".join(notes)
