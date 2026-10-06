"""Document facade: preview and export share ONE pipeline (spec 33).

UI/batch call DocumentService.render() for preview AND for export - the same
pixels are then handed to export_engine. No parallel render paths.
"""
from document_engine.dimensions import Units


class DocumentService:
    def __init__(self, hw_engine, template_manager):
        self.hw = hw_engine
        self.templates = template_manager

    def render(self, template_id, fields, profile_id, settings):
        """Single page -> (PIL image, warnings, info with physical size)."""
        tpl = self.templates.get(template_id)
        dpi = int(settings.get("dpi", tpl.dpi))
        geo = tpl.geometry(dpi)  # canvas_px + areas
        img, warnings, info = self.hw.render_document(geo, fields,
                                                      profile_id, settings)
        info.update({"template": template_id, "dpi": dpi,
                     "size_in": (tpl.width_in, tpl.height_in),
                     "size_pt": Units.page_pt(tpl.width_in, tpl.height_in)})
        return img, warnings, info

    def render_paginated(self, template_id, fields, profile_id, settings):
        """Multi page -> ([PIL images], warnings, info with physical size)."""
        tpl = self.templates.get(template_id)
        dpi = int(settings.get("dpi", tpl.dpi))
        geo = tpl.geometry(dpi)
        pages, warnings, info = self.hw.render_document_paginated(
            geo, fields, profile_id, settings)
        info.update({"template": template_id, "dpi": dpi,
                     "size_in": (tpl.width_in, tpl.height_in),
                     "size_pt": Units.page_pt(tpl.width_in, tpl.height_in)})
        return pages, warnings, info
