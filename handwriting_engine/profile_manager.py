"""Profile manager: dynamic discovery + CRUD + import/export (spec 5, 22-23)."""
import json
import os
import shutil
import tempfile
import zipfile

from handwriting_engine.profile import (ProfileError, load_profile,
                                        validate_profile)


class ProfileManager:
    def __init__(self, profiles_dir, bundled_dir=None):
        self.profiles_dir = profiles_dir
        self.bundled_dir = bundled_dir
        os.makedirs(self.profiles_dir, exist_ok=True)
        self._cache = {}

    def _all_dirs(self):
        ids = {}
        for base in (self.bundled_dir, self.profiles_dir):
            if base and os.path.isdir(base):
                for pid in sorted(os.listdir(base)):
                    if os.path.isdir(os.path.join(base, pid)):
                        ids.setdefault(pid, base)
        return ids

    def list_ids(self):
        return sorted(self._all_dirs())

    def _base_for(self, profile_id):
        return self._all_dirs().get(profile_id, self.profiles_dir)

    def get(self, profile_id, fresh=False):
        if fresh or profile_id not in self._cache:
            self._cache[profile_id] = load_profile(
                self._base_for(profile_id), profile_id)
            # normalize dir to real location
            self._cache[profile_id]["dir"] = os.path.join(
                self._base_for(profile_id), profile_id)
        return self._cache[profile_id]

    def list_profiles(self):
        out = []
        for pid in self.list_ids():
            try:
                out.append(self.get(pid))
            except ProfileError:
                continue
        return out

    def validate(self, profile_id):
        return validate_profile(self.get(profile_id, fresh=True))

    # ---- CRUD ----
    def delete(self, profile_id):
        d = os.path.join(self.profiles_dir, profile_id)
        if not os.path.isdir(d):
            raise ProfileError("Only user profiles can be deleted "
                               "(bundled profiles are read-only).")
        shutil.rmtree(d, ignore_errors=True)
        self._cache.pop(profile_id, None)

    def save_meta(self, profile_id, meta, config):
        d = os.path.join(self.profiles_dir, profile_id)
        os.makedirs(os.path.join(d, "glyphs"), exist_ok=True)
        with open(os.path.join(d, "metadata.json"), "w",
                  encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        with open(os.path.join(d, "configuration.json"), "w",
                  encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        self._cache.pop(profile_id, None)

    # ---- portable .hwprofile (zip) ----
    def export_zip(self, profile_id, dest_path):
        src = os.path.join(self._base_for(profile_id), profile_id)
        with zipfile.ZipFile(dest_path, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _ds, files in os.walk(src):
                for fn in files:
                    full = os.path.join(root, fn)
                    z.write(full, os.path.relpath(full, src))
        return dest_path

    def import_zip(self, zip_path, profile_id=None):
        with zipfile.ZipFile(zip_path) as z:
            names = z.namelist()
            if "metadata.json" not in names:
                raise ProfileError("Not a handwriting profile: "
                                   "metadata.json missing.")
            meta = json.loads(z.read("metadata.json").decode("utf-8"))
            pid = profile_id or "".join(
                c if (c.isalnum() or c in "-_") else "-" for c in
                meta.get("name", "imported").lower()).strip("-") or "imported"
            dest = os.path.join(self.profiles_dir, pid)
            if os.path.isdir(dest):
                raise ProfileError(f"Profile id '{pid}' already exists.")
            with tempfile.TemporaryDirectory() as tmp:
                z.extractall(tmp)
                shutil.copytree(tmp, dest)
            # validate after import
            warnings = self.validate(pid)
            self._cache.pop(pid, None)
            return pid, warnings
