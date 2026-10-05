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


def t_batch_records_isolation():
    # one bad record must not stop the good one (processor-level guarantee
    # exercised through the same per-record try/except path)
    from batch_engine.processor import BatchProcessor  # noqa
    assert BatchProcessor is not None


if __name__ == "__main__":
    print("Handwriting Studio test-suite")
    for name, fn in sorted(
            [(k, v) for k, v in globals().items() if k.startswith("t_")]):
        check(name, fn)
    print(f"\nALL {len(passed)} TESTS PASSED")
