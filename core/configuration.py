"""Application settings (spec section 30), stored as JSON. Offline-first."""
import json
import os

DEFAULTS = {
    "default_template": "four_by_six",
    "default_profile": "classic-script",
    "export_dir": "",
    "dpi": 300,
    "default_variation": 0.6,
    "default_font_size": 42,
    "pdf_format": True,
    "png_format": True,
    "naming": "{template}_{profile}_{seed}_{date}",
    "theme": "light",
    "recent_limit": 8,
}


class AppSettings:
    def __init__(self, path):
        self.path = path
        self.data = dict(DEFAULTS)
        self.load()

    def load(self):
        try:
            if os.path.isfile(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                for k, v in saved.items():
                    if k in DEFAULTS:
                        self.data[k] = v
        except Exception:
            pass
        return self

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception:
            pass

    def get(self, key, default=None):
        return self.data.get(key, DEFAULTS.get(key, default))

    def set(self, key, value):
        if key in DEFAULTS:
            self.data[key] = value
            self.save()

    def reset(self):
        self.data = dict(DEFAULTS)
        self.save()
