"""Consistent monochrome stroke icon set (spec 49).

Drawn at runtime with QPainter: crisp at any DPI, no asset files, identical
on Windows and macOS. Single 2px visual language, round caps/joins.
"""
from PySide6.QtGui import (QPixmap, QPainter, QPen, QColor, QPainterPath,
                           QPolygonF)
from PySide6.QtCore import Qt, QPointF

BASE_SIZE = 60
STROKE = 4.6
COLOR = "#D4D4D8"


def _pix(draw_fn, color=COLOR):
    pm = QPixmap(BASE_SIZE, BASE_SIZE)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(STROKE)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    draw_fn(p)
    p.end()
    return pm


def _dashboard(p):
    for x, y in ((13, 13), (32, 13), (13, 32), (32, 32)):
        p.drawRoundedRect(x, y, 15, 15, 3.5, 3.5)


def _creator(p):
    # pencil, 45 degrees
    p.save()
    p.translate(30, 30)
    p.rotate(45)
    p.drawRoundedRect(-4, -20, 8, 26, 2.5, 2.5)
    p.drawPolyline(QPolygonF([QPointF(-4, 6), QPointF(0, 20),
                              QPointF(4, 6)]))
    p.restore()


def _templates(p):
    # overlapping pages
    p.drawRoundedRect(22, 10, 24, 32, 3, 3)
    p.drawRoundedRect(14, 18, 24, 32, 3, 3)


def _profiles(p):
    # user: head + shoulders
    p.drawEllipse(21, 10, 18, 18)
    path = QPainterPath()
    path.moveTo(12, 52)
    path.cubicTo(12, 40, 20, 36, 30, 36)
    path.cubicTo(40, 36, 48, 40, 48, 52)
    p.drawPath(path)


def _training(p):
    # sparkle
    p.drawPolyline(QPolygonF([
        QPointF(30, 8), QPointF(34.5, 25.5), QPointF(52, 30),
        QPointF(34.5, 34.5), QPointF(30, 52), QPointF(25.5, 34.5),
        QPointF(8, 30), QPointF(25.5, 25.5), QPointF(30, 8)]))


def _batch(p):
    # stacked bars
    for y, x0, x1 in ((18, 12, 48), (30, 17, 43), (42, 22, 38)):
        p.drawLine(int(x0), y, int(x1), y)


def _exports(p):
    # download into tray
    p.drawLine(30, 10, 30, 34)
    p.drawPolyline(QPolygonF([QPointF(21, 26), QPointF(30, 35),
                              QPointF(39, 26)]))
    p.drawPolyline(QPolygonF([QPointF(14, 40), QPointF(14, 50),
                              QPointF(46, 50), QPointF(46, 40)]))


def _settings(p):
    # gear: ring + 8 teeth
    import math
    cx = cy = 30.0
    for k in range(8):
        a = math.pi / 4 * k
        p.drawLine(int(cx + 13 * math.cos(a)), int(cy + 13 * math.sin(a)),
                   int(cx + 20 * math.cos(a)), int(cy + 20 * math.sin(a)))
    p.drawEllipse(21, 21, 18, 18)


_DRAW = {"dashboard": _dashboard, "creator": _creator,
         "templates": _templates, "profiles": _profiles,
         "training": _training, "batch": _batch, "exports": _exports,
         "settings": _settings}

_cache = {}


def icon(name, color=COLOR):
    key = (name, color)
    if key not in _cache:
        fn = _DRAW.get(name)
        if fn is None:
            raise KeyError(f"Unknown icon '{name}'")
        _cache[key] = _pix(fn, color)
    return _cache[key]


def available():
    return sorted(_DRAW)
