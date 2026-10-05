"""Profile validation for built/imported profiles (spec 52)."""
import os

from handwriting_engine.profile import load_profile, validate_profile


def validate_new_profile(profiles_dir, profile_id, required_chars=None):
    prof = load_profile(profiles_dir, profile_id)
    warnings = validate_profile(prof, required_chars)
    glyph_dir = os.path.join(profiles_dir, profile_id, "glyphs")
    n_files = (len([f for f in os.listdir(glyph_dir)
                    if f.endswith(".png")])
               if os.path.isdir(glyph_dir) else 0)
    return {"warnings": warnings, "glyph_files": n_files,
            "supported": len(prof["supported"]),
            "ok": not warnings or all("fallback" not in w.lower()
                                      and "missing" not in w.lower()
                                      for w in warnings)}
