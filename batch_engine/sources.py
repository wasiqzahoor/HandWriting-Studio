"""Batch sources: CSV + TXT loading (spec 26-27)."""
import csv
import os


def load_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row.")
        rows = [{(k or "").strip(): (v or "") for k, v in r.items()}
                for r in reader]
    rows = [r for r in rows if any(v.strip() for v in r.values())]
    if not rows:
        raise ValueError("CSV contains no data rows.")
    return reader.fieldnames, rows


def load_txt(path, mode="line"):
    """mode 'line': one doc per non-empty line.
    mode 'block': docs split on blank lines."""
    with open(path, encoding="utf-8-sig") as f:
        text = f.read()
    if mode == "block":
        blocks = [b.strip() for b in text.split("\n\n")]
        rows = [{"text": b} for b in blocks if b]
    else:
        rows = [{"text": ln.strip()} for ln in text.splitlines()
                if ln.strip()]
    if not rows:
        raise ValueError("TXT file has no usable content.")
    return ["text"], rows


def load_source(path, txt_mode="line"):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return load_csv(path)
    if ext == ".txt":
        return load_txt(path, txt_mode)
    raise ValueError(f"Unsupported batch source '{ext}' (use CSV or TXT).")
