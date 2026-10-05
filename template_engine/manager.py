"""TemplateManager: built-ins + user templates in JSON (spec 19)."""
import json
import os

from template_engine.templates import Template, builtin_templates


class TemplateManager:
    def __init__(self, store_dir):
        self.store_dir = store_dir
        os.makedirs(store_dir, exist_ok=True)
        self._templates = {t.template_id: t for t in builtin_templates()}
        self.reload_custom()

    def reload_custom(self):
        for fn in os.listdir(self.store_dir):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(self.store_dir, fn),
                          encoding="utf-8") as f:
                    t = Template.from_dict(json.load(f))
                t.builtin = False
                self._templates[t.template_id] = t
            except Exception:
                continue

    def list(self):
        return sorted(self._templates.values(),
                      key=lambda t: (t.kind, t.name))

    def get(self, template_id):
        if template_id not in self._templates:
            raise KeyError(f"Unknown template '{template_id}'")
        return self._templates[template_id]

    def save_custom(self, template):
        template.builtin = False
        path = os.path.join(self.store_dir, f"{template.template_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(template.to_dict(), f, indent=2)
        self._templates[template.template_id] = template

    def duplicate(self, template_id, new_id, new_name):
        src = self.get(template_id)
        d = src.to_dict()
        d.update(id=new_id, name=new_name, builtin=False, is_default=False)
        t = Template.from_dict(d)
        self.save_custom(t)
        return t

    def delete(self, template_id):
        t = self.get(template_id)
        if t.builtin:
            raise ValueError("Built-in templates cannot be deleted.")
        path = os.path.join(self.store_dir, f"{template_id}.json")
        if os.path.isfile(path):
            os.remove(path)
        del self._templates[template_id]

    def set_default(self, template_id):
        for t in self._templates.values():
            t.is_default = (t.template_id == template_id)
            if not t.builtin:
                self.save_custom(t)

    def default_id(self):
        for t in self._templates.values():
            if t.is_default:
                return t.template_id
        return "four_by_six"
