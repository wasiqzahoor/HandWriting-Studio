"""Handwriting profile: load + validate (spec sections 8, 52, 54)."""
import json
import os

REQUIRED_META = ("name", "version", "renderer")
PRINTABLE = [chr(c) for c in range(32, 127)]


class ProfileError(Exception):
    pass


def profile_dir(base_profiles, profile_id):
    return os.path.join(base_profiles, profile_id)


def load_profile(base_profiles, profile_id):
    """Returns dict with meta + config + glyph stats. Raises ProfileError."""
    d = profile_dir(base_profiles, profile_id)
    meta_p = os.path.join(d, "metadata.json")
    if not os.path.isfile(meta_p):
        raise ProfileError(f"Profile '{profile_id}' has no metadata.json")
    try:
        with open(meta_p, encoding="utf-8") as f:
            meta = json.load(f)
    except Exception as e:
        raise ProfileError(f"Profile '{profile_id}': bad metadata.json ({e})")
    for k in REQUIRED_META:
        if k not in meta:
            raise ProfileError(f"Profile '{profile_id}': missing '{k}'")
    cfg = {}
    cfg_p = os.path.join(d, "configuration.json")
    if os.path.isfile(cfg_p):
        try:
            with open(cfg_p, encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            pass
    from handwriting_engine.glyph_manager import GlyphManager
    gm = GlyphManager(glyphs_dir=os.path.join(d, "glyphs"),
                      font_path=cfg.get("base_font"),
                      ink_color=tuple(cfg.get("ink", [30, 42, 92])))
    supported = sorted(gm.asset_chars)
    return {"id": profile_id, "dir": d, "meta": meta, "config": cfg,
            "supported": supported, "glyph_manager": gm}


def validate_profile(prof, required_chars=None):
    """Returns list of warning strings (empty = healthy)."""
    warnings = []
    meta = prof["meta"]
    try:
        float(str(meta.get("version", "1.0")))
    except Exception:
        warnings.append("Profile version is not numeric.")
    supported = set(prof["supported"])
    if not supported:
        warnings.append("Profile has no glyph assets; pure font fallback "
                        "will be used for every character.")
    check = required_chars or [c for c in PRINTABLE if c not in (" ", "\t")]
    missing = [c for c in check if c not in supported]
    if missing:
        shown = "".join(missing[:20])
        warnings.append(f"This profile is missing {len(missing)} characters "
                        f"({shown}...). Those will use fallback rendering.")
    return warnings


def coverage_report(prof):
    supported = set(prof["supported"])
    groups = {"uppercase": [chr(c) for c in range(65, 91)],
              "lowercase": [chr(c) for c in range(97, 123)],
              "digits": [chr(c) for c in range(48, 58)],
              "punctuation": list(".,?!'\"-:;()& ")}
    out = {}
    for g, chars in groups.items():
        hit = [c for c in chars if c in supported or c == " "]
        out[g] = {"have": len(hit), "total": len(chars),
                  "missing": [c for c in chars if c not in supported and c != " "]}
    return out
