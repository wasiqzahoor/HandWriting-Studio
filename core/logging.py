"""Centralized logging (spec section 39). File + console, local only."""
import logging
import os
import sys

_configured = False


def setup_logging(logs_dir, level=logging.INFO):
    global _configured
    os.makedirs(logs_dir, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(level)
    if not _configured:
        fh = logging.FileHandler(os.path.join(logs_dir, "studio.log"),
                                 encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(fmt)
        root.addHandler(ch)
        _configured = True
    return root


def get_logger(name):
    return logging.getLogger(name)
