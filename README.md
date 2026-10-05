# Handwriting Studio v1.0.0 - Cross-Platform Desktop Application

Professional handwriting-style document generator for **Windows 10/11** and
**macOS (Apple Silicon + Intel)**. Fully offline - no AI APIs, no cloud.

## Pages

| Page | What it does |
|---|---|
| Dashboard | Stats, quick actions, recent documents |
| Document Creator | Template + profile + text + controls, live preview, PDF/PNG export |
| Templates | 4x6 card + #10 envelope cards, create/edit/duplicate/delete, thumbnails |
| Profiles | Profile cards with previews, validation, import/export (.hwprofile) |
| Training | 6-step wizard: upload -> analyze -> coverage -> build -> validate -> save |
| Batch Jobs | CSV/TXT import, field mapping, progress, per-record errors, retry |
| Exports | Full export history with open/reveal/copy/delete |
| Settings | Defaults, DPI, formats, naming, light/dark theme, logs, reset |

## Run

Windows:

```bat
pip install -r requirements.txt
run.bat
```

macOS / Linux:

```sh
pip3 install -r requirements.txt
sh run.sh
```

Portable/dev mode (data inside `./.data`):

```sh
python main.py --portable
```

## Architecture

```
PySide6 UI (ui/)          <- knows nothing about glyph internals
Application layer (core/application.py)
Template engine + Batch processor + Profile manager
Handwriting engine (handwriting_engine/)
    Glyph model / Stroke model (placeholder) / Variation model
Rendering -> PDF / Image export
Training pipeline (training/) -> portable .hwprofile
```

- `HandwritingEngine.render_document()` is the single pipeline used by both
  preview and export - there is no second render path.
- Profiles are independent data (`handwriting_engine/profiles/<id>/` with
  `metadata.json`, `configuration.json`, `glyphs/` incl. `_vN` variants).
- The glyph builder output is honestly labelled everywhere; the renderer
  interface accepts future Stroke/Neural renderers without UI changes.
- App data lives in OS directories (spec 38); SQLite holds
  documents/jobs/records/exports; settings are JSON.

## Tests

```sh
python -m pytest tests/ -v
# or
python tests/test_app.py
```

Covers: profile loading/validation/rendering/seed determinism, 4x6 + #10
dimensions, margins/wrapping, PDF/PNG sizes, CSV parsing, invalid rows,
batch record isolation.

## Printing

PDFs are exact physical size (4x6in = 288x432pt, #10 = 297x684pt). In the
print dialog disable scaling ("Actual size", no fit-to-page) and verify
printer margins before production runs.
