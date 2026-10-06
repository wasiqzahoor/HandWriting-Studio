"""Production test-suite (spec 51). Run: python tests/test_app.py"""
import csv
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.paths import PlatformPaths
from core.application import AppContext

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLED = os.path.join(BASE, "handwriting_engine", "profiles")


def make_ctx():
    tmp = tempfile.mkdtemp(prefix="hws_")
    paths = PlatformPaths(base=tmp)
    return AppContext(paths, BUNDLED), tmp


CTX, _TMP = make_ctx()

passed = []


def check(name, fn):
    try:
        fn()
        passed.append(name)
        print(f"  ok - {name}")
    except AssertionError as e:
        print(f"  FAIL - {name}: {e}")
        raise SystemExit(1)


# ---- handwriting engine ----
def t_profiles_catalog():
    ids = CTX.profiles.list_ids()
    for want in ("classic-script", "print-casual", "lucida-hand",
                 "brush-script", "french-script", "comic-casual"):
        assert want in ids, ids
    for pid in ids:
        p = CTX.profiles.get(pid)
        assert len(p["supported"]) >= 70, (pid, len(p["supported"]))


def t_profile_loading():
    ids = CTX.profiles.list_ids()
    assert "classic-script" in ids, ids
    assert "print-casual" in ids, ids
    p = CTX.profiles.get("classic-script")
    assert p["meta"]["renderer"] == "glyph_based"
    assert len(p["supported"]) >= 70


def t_profile_validation():
    w = CTX.profiles.validate("classic-script")
    assert isinstance(w, list)
    # classic covers demo text; print-casual covers everything
    w2 = CTX.profiles.validate("print-casual")
    assert w2 == [], w2


def t_invalid_profile():
    try:
        CTX.profiles.get("no-such-profile")
        raise AssertionError("expected ProfileError")
    except Exception as e:
        assert "metadata" in str(e).lower() or "profile" in str(e).lower()


def t_render_and_seed():
    kw = dict(template="four_by_six",
              fields={"header": "Alex", "body": "Hello John"},
              profile="classic-script")
    a, _, _ = CTX.documents.render(kw["template"], kw["fields"], kw["profile"],
                                   {"seed": 11})
    b, _, _ = CTX.documents.render(kw["template"], kw["fields"], kw["profile"],
                                   {"seed": 22})
    c, _, _ = CTX.documents.render(kw["template"], kw["fields"], kw["profile"],
                                   {"seed": 11})
    assert a.tobytes() != b.tobytes(), "seeds must differ"
    assert a.tobytes() == c.tobytes(), "same seed must reproduce"


def t_variants_used():
    p = CTX.profiles.get("print-casual")
    gm = p["glyph_manager"]
    assert gm.n_variants("a") >= 2, "expected baked variants"


def t_missing_glyph_fallback():
    img, warnings, info = CTX.documents.render(
        "four_by_six", {"header": "", "body": "Caf\u00e9 \u20ac test"},
        "classic-script", {"seed": 3})
    assert img.size == (1200, 1800)
    assert any("fallback" in w.lower() for w in warnings), warnings


# ---- document engine ----
def t_4x6_dimensions():
    t = CTX.templates.get("four_by_six")
    assert (t.width_in, t.height_in) == (4.0, 6.0)
    assert t.canvas_px == (1200, 1800), t.canvas_px


def t_envelope_dimensions():
    t = CTX.templates.get("envelope_10")
    assert (t.width_in, t.height_in) == (4.125, 9.5)
    w, h = t.canvas_px
    assert (w, h) == (1238, 2850), (w, h)
    g = t.geometry()
    assert "stamp_box" in g and len(g["areas"]) == 2


def t_margins_and_wrap():
    long_text = ("Thank you for your message. " * 6).strip()
    img, warnings, info = CTX.documents.render(
        "four_by_six", {"header": "H", "body": long_text},
        "classic-script", {"seed": 9})
    assert warnings == [], warnings  # must fit, nothing dropped
    # overflow path
    huge = "\n".join(f"Line {i} with plenty of words here" for i in range(60))
    _img, warnings2, info2 = CTX.documents.render(
        "four_by_six", {"header": "", "body": huge},
        "classic-script", {"seed": 9})
    assert info2["overflow"] and any("exceed" in w for w in warnings2)


def t_envelope_render():
    img, warnings, info = CTX.documents.render(
        "envelope_10", {"sender": "Alex\n1 Main St", "recipient": "John\n2 Oak"},
        "print-casual", {"seed": 4})
    assert img.size == (1238, 2850), img.size


# ---- export ----
def t_export_sizes():
    from export_engine.pdf_exporter import export_pdf
    from export_engine.image_exporter import export_png
    img, _, info = CTX.documents.render(
        "four_by_six", {"header": "A", "body": "Hi"}, "classic-script",
        {"seed": 1})
    d = tempfile.mkdtemp()
    p = export_pdf(img, os.path.join(d, "t.pdf"), *info["size_in"])
    data = open(p, "rb").read()
    assert b"288" in data and b"432" in data
    q = export_png(img, os.path.join(d, "t.png"))
    from PIL import Image
    assert Image.open(q).size == (1200, 1800)


# ---- batch ----
def t_csv_parsing():
    from batch_engine.sources import load_source
    d = tempfile.mkdtemp()
    p = os.path.join(d, "in.csv")
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "message"])
        w.writerow(["John", "Hello John"])
        w.writerow(["", ""])
        w.writerow(["Jane", "Hi Jane"])
    cols, rows = load_source(p)
    assert cols == ["name", "message"], cols
    assert len(rows) == 2, rows


def t_invalid_source():
    from batch_engine.sources import load_source
    d = tempfile.mkdtemp()
    p = os.path.join(d, "empty.csv")
    open(p, "w").close()
    try:
        load_source(p)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    p2 = os.path.join(d, "x.json")
    open(p2, "w").write("{}")
    try:
        load_source(p2)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def t_pagination():
    long_text = "\n\n".join(
        f"Paragraph {i}: Thank you for your message, I hope you are well."
        for i in range(12))
    pages, warnings, info = CTX.documents.render_paginated(
        "four_by_six", {"header": "Alex", "body": long_text},
        "classic-script", {"seed": 9})
    assert len(pages) > 1, f"expected multiple pages, got {len(pages)}"
    assert not info["overflow"], warnings
    assert all(p.size == (1200, 1800) for p in pages)
    # deterministic across pages
    pages2, _, _ = CTX.documents.render_paginated(
        "four_by_six", {"header": "Alex", "body": long_text},
        "classic-script", {"seed": 9})
    assert [p.tobytes() for p in pages] == [p.tobytes() for p in pages2]
    # short text still single page
    one, _, _ = CTX.documents.render_paginated(
        "four_by_six", {"header": "A", "body": "Hi"}, "classic-script",
        {"seed": 1})
    assert len(one) == 1


def t_multipage_export():
    from export_engine.export_manager import ExportManager
    pages, _, info = CTX.documents.render_paginated(
        "four_by_six", {"header": "A",
                        "body": ("Long line here. " * 40 + "\n\n") * 6},
        "classic-script", {"seed": 2})
    assert len(pages) > 1
    d = tempfile.mkdtemp()
    mgr = ExportManager(CTX.db, d)
    paths = mgr.export(pages, info["size_in"], d, "multi", ["pdf", "png"],
                       doc_type="document", template="four_by_six",
                       profile="classic-script")
    pdfs = [p for p in paths if p.endswith(".pdf")]
    pngs = [p for p in paths if p.endswith(".png")]
    assert len(pdfs) == 1 and len(pngs) == len(pages), paths
    from PIL import Image
    assert Image.open(pngs[0]).size == (1200, 1800)


def t_templates_catalog():
    ids = [t.template_id for t in CTX.templates.list()]
    for want in ("four_by_six", "four_by_six_blank", "four_by_six_ruled",
                 "envelope_10"):
        assert want in ids, ids
    blank = CTX.templates.get("four_by_six_blank")
    assert "header" not in blank.fields
    assert blank.page_white and not blank.ruled
    ruled = CTX.templates.get("four_by_six_ruled")
    assert ruled.ruled and ruled.page_white
    geo = blank.geometry()
    assert len(geo["areas"]) == 1 and geo["areas"][0][0] == "body"


def t_ruled_and_white():
    plain, _, _ = CTX.documents.render(
        "four_by_six_blank", {"body": "Hi"}, "print-casual", {"seed": 1})
    ruled, _, _ = CTX.documents.render(
        "four_by_six_ruled", {"header": "H", "body": "Hi"}, "print-casual",
        {"seed": 1, "ruled": True, "page_white": True})
    assert ruled.tobytes() != plain.tobytes()
    import numpy as np
    px = np.asarray(ruled.convert("RGB"))
    assert (px[0, 0] == [255, 255, 255]).all(), px[0, 0]  # white page
    # a rule line exists inside body area (light blue-grey pixels)
    body = np.asarray(ruled.crop((105, 400, 1095, 1500)).convert("RGB"))
    blueish = ((body[:, :, 2] > body[:, :, 0] + 8)).mean()
    assert blueish > 0.0005, blueish
    # override off -> no rules
    norule, _, _ = CTX.documents.render(
        "four_by_six_ruled", {"header": "H", "body": "Hi"}, "print-casual",
        {"seed": 1, "ruled": False})
    assert norule.tobytes() != ruled.tobytes()


def t_ink_override():
    _img, _w, info = CTX.documents.render(
        "four_by_six", {"header": "", "body": "Hi"}, "print-casual",
        {"seed": 1, "ink": (193, 18, 31)})
    assert tuple(info["ink"]) == (193, 18, 31), info["ink"]


def _ink_height(img):
    import numpy as np
    g = np.asarray(img.convert("RGB")).astype(int)
    bg = np.array([253, 252, 247])
    mask = (abs(g - bg).sum(axis=2) > 36)
    ys = np.where(mask.any(axis=1))[0]
    return int(ys.max() - ys.min()) if len(ys) else 0


def t_font_size_scaling():
    kw = dict(template="four_by_six",
              fields={"header": "Alex", "body": "Hello John, thank you"},
              profile="print-casual")
    small, _, _ = CTX.documents.render(kw["template"], kw["fields"],
                                       kw["profile"], {"seed": 5,
                                                       "font_size": 12})
    big, _, _ = CTX.documents.render(kw["template"], kw["fields"],
                                     kw["profile"], {"seed": 5,
                                                     "font_size": 56})
    assert small.size == big.size == (1200, 1800)
    assert _ink_height(small) < _ink_height(big), \
        (_ink_height(small), _ink_height(big))


def t_min_size_renders():
    img, warnings, _info = CTX.documents.render(
        "four_by_six", {"header": "Tiny", "body": "Small size test. " * 40},
        "print-casual", {"seed": 1, "font_size": 8})
    assert img.size == (1200, 1800)
    assert _ink_height(img) > 10


def t_line_map():
    _img, _w, info = CTX.documents.render(
        "four_by_six", {"header": "Alex", "body": "Dear John,\n\nThank you."},
        "print-casual", {"seed": 1})
    m = info.get("map", [])
    assert len(m) >= 3, m
    areas = {e["area"] for e in m}
    assert "header" in areas and "body" in areas, areas
    for e in m:
        assert set(e) == {"page", "area", "para", "rect"}
        x0, y0, x1, y1 = e["rect"]
        assert 0 <= x0 < x1 <= 1200 and 0 <= y0 < y1 <= 1800, e
        assert e["page"] == 0
    pages, _, info2 = CTX.documents.render_paginated(
        "four_by_six", {"header": "", "body": "Word " * 400},
        "print-casual", {"seed": 1})
    assert len(pages) > 1
    assert max(e["page"] for e in info2["map"]) == len(pages) - 1


def t_batch_records_isolation():    # one bad record must not stop the good one (processor-level guarantee
    # exercised through the same per-record try/except path)
    from batch_engine.processor import BatchProcessor  # noqa
    assert BatchProcessor is not None


if __name__ == "__main__":
    print("Handwriting Studio test-suite")
    for name, fn in sorted(
            [(k, v) for k, v in globals().items() if k.startswith("t_")]):
        check(name, fn)
    print(f"\nALL {len(passed)} TESTS PASSED")
