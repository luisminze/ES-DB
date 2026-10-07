"""Widgets reutilizáveis: indicadores, capas, barras de ranking."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (QBrush, QColor, QIcon, QPainter, QPen, QPixmap,
                           QPolygonF, QRadialGradient)
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget)

from ..domain.calculations import Ranked, format_duration

_COVER_CACHE: dict[tuple[str, int, int], QPixmap] = {}

# Cor da aura de raridade por grau (estilo Steam): platina azulada, ouro dourado.
GRADE_GLOW = {"platinum": QColor("#79C7FF"), "gold": QColor("#FFC340")}


def _paint_icon(kind: str, size: int, color: str) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(1.8)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    s = size
    if kind == "funnel":
        m = s * 0.2
        poly = QPolygonF([
            QPointF(m, m), QPointF(s - m, m), QPointF(s * 0.58, s * 0.5),
            QPointF(s * 0.58, s - m), QPointF(s * 0.42, s - m * 0.8),
            QPointF(s * 0.42, s * 0.5)])
        p.drawPolyline(poly)
        p.drawLine(QPointF(m, m), QPointF(s - m, m))
    elif kind == "refresh":
        rect = QRectF(s * 0.22, s * 0.22, s * 0.56, s * 0.56)
        p.drawArc(rect, 40 * 16, 260 * 16)
        # seta
        tip = QPointF(s * 0.74, s * 0.30)
        p.drawLine(tip, QPointF(s * 0.60, s * 0.26))
        p.drawLine(tip, QPointF(s * 0.70, s * 0.44))
    elif kind == "gear":
        import math
        cx, cy = s / 2, s / 2
        rout, rin = s * 0.34, s * 0.2
        teeth = QPolygonF()
        for i in range(16):
            r = rout if i % 2 == 0 else rin
            ang = math.pi * i / 8
            teeth.append(QPointF(cx + r * math.cos(ang), cy + r * math.sin(ang)))
        p.drawPolygon(teeth)
        p.drawEllipse(QPointF(cx, cy), s * 0.1, s * 0.1)
    p.end()
    return QIcon(pix)


def nav_icon(kind: str, color: str = "#E8EAED", size: int = 20) -> QIcon:
    """Ícone desenhado para a barra superior: funnel, refresh, gear."""
    return _paint_icon(kind, size, color)


def stat_tile(value: str, label: str, accent: bool = False) -> QFrame:
    tile = QFrame()
    tile.setObjectName("Tile")
    lay = QVBoxLayout(tile)
    lay.setContentsMargins(16, 14, 16, 14)
    lay.setSpacing(2)
    v = QLabel(value)
    v.setObjectName("TileAccent" if accent else "TileValue")
    lab = QLabel(label)
    lab.setObjectName("TileLabel")
    lab.setWordWrap(True)
    lay.addWidget(v)
    lay.addWidget(lab)
    return tile


def section_title(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("SectionTitle")
    return lab


def load_cover(path: str | None, width: int, height: int,
               crop: bool = False) -> QPixmap | None:
    """Carrega a capa.

    - ``crop=False`` (padrão): **respeita o aspecto original**, escalando para
      caber dentro de ``width×height`` sem cortar nem distorcer.
    - ``crop=True``: preenche a caixa recortando o excedente (uso antigo).
    """
    if not path or not Path(path).is_file():
        return None
    key = (path, width, height, crop)
    cached = _COVER_CACHE.get(key)
    if cached is not None:
        return cached
    pix = QPixmap(path)
    if pix.isNull():
        return None
    if crop:
        scaled = pix.scaled(width, height, Qt.KeepAspectRatioByExpanding,
                            Qt.SmoothTransformation)
        if scaled.width() > width or scaled.height() > height:
            x = max(0, (scaled.width() - width) // 2)
            y = max(0, (scaled.height() - height) // 2)
            scaled = scaled.copy(x, y, width, height)
    else:
        scaled = pix.scaled(width, height, Qt.KeepAspectRatio,
                            Qt.SmoothTransformation)
    _COVER_CACHE[key] = scaled
    return scaled


def cover_label(path: str | None, title: str, width: int, height: int,
                crop: bool = False) -> QLabel:
    lab = QLabel()
    lab.setFixedSize(width, height)
    lab.setAlignment(Qt.AlignCenter)
    pix = load_cover(path, width, height, crop)
    if pix is not None:
        lab.setObjectName("Cover")
        lab.setPixmap(pix)
    else:
        lab.setObjectName("Placeholder")
        initials = "".join(w[0] for w in title.split()[:2]).upper() or "?"
        lab.setText(initials)
    return lab


def cover_fit_label(path: str | None, title: str, width: int) -> QLabel:
    """Capa com **largura fixa e altura dinâmica** conforme o aspecto da imagem
    original — nada é cortado ou esticado."""
    pix = QPixmap(path) if (path and Path(path).is_file()) else QPixmap()
    lab = QLabel()
    lab.setAlignment(Qt.AlignCenter)
    if not pix.isNull():
        key = ("fitw", path, width)
        scaled = _COVER_CACHE.get(key)
        if scaled is None:
            scaled = pix.scaledToWidth(width, Qt.SmoothTransformation)
            _COVER_CACHE[key] = scaled
        lab.setObjectName("Cover")
        lab.setFixedSize(scaled.size())
        lab.setPixmap(scaled)
    else:
        lab.setObjectName("Placeholder")
        lab.setFixedSize(width, int(width * 1.5))
        lab.setText("".join(w[0] for w in title.split()[:2]).upper() or "?")
    return lab


def _dim_pixmap(pix: QPixmap, darkness: int = 160) -> QPixmap:
    """Escurece um pixmap preservando a forma (troféu bloqueado)."""
    out = QPixmap(pix.size())
    out.fill(Qt.transparent)
    p = QPainter(out)
    p.drawPixmap(0, 0, pix)
    p.setCompositionMode(QPainter.CompositionMode_SourceAtop)
    p.fillRect(out.rect(), QColor(0, 0, 0, darkness))
    p.end()
    return out


def trophy_icon(path: str | None, title: str, size: int, unlocked: bool,
                grade_value: str) -> QLabel:
    """Ícone de troféu com escurecimento (bloqueado) e aura de raridade
    (ouro/platina), no estilo Steam. O brilho é desenhado no próprio pixmap."""
    glow = GRADE_GLOW.get(grade_value)
    base = load_cover(path, size, size)
    if base is None:
        return cover_label(path, title, size, size)

    pad = 15 if glow is not None else 0
    total = size + pad * 2
    lab = QLabel()
    lab.setFixedSize(total, total)
    lab.setAlignment(Qt.AlignCenter)

    canvas = QPixmap(total, total)
    canvas.fill(Qt.transparent)
    p = QPainter(canvas)
    p.setRenderHint(QPainter.Antialiasing)
    if glow is not None:
        grad = QRadialGradient(QPointF(total / 2, total / 2), total / 2)
        inner = QColor(glow); inner.setAlpha(235 if unlocked else 130)
        mid = QColor(glow); mid.setAlpha(130 if unlocked else 60)
        edge = QColor(glow); edge.setAlpha(0)
        grad.setColorAt(0.40, inner)
        grad.setColorAt(0.68, mid)
        grad.setColorAt(1.0, edge)
        p.fillRect(canvas.rect(), QBrush(grad))
    icon = base if unlocked else _dim_pixmap(base)
    p.drawPixmap(pad, pad, icon)
    p.end()
    lab.setPixmap(canvas)
    return lab


class BarRow(QWidget):
    """Linha de ranking: rótulo + barra proporcional + valor absoluto."""

    def __init__(self, label: str, seconds: float, maximum: float,
                 suffix: str = "") -> None:
        super().__init__()
        self.setMinimumHeight(42)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(4)
        top = QHBoxLayout()
        name = QLabel(label)
        name.setTextFormat(Qt.PlainText)
        val = QLabel(format_duration(seconds) + suffix)
        val.setObjectName("CardMeta")
        val.setAlignment(Qt.AlignRight)
        top.addWidget(name, 1)
        top.addWidget(val)
        lay.addLayout(top)

        track = QFrame()
        track.setObjectName("Bar")
        track.setFixedHeight(10)
        tl = QHBoxLayout(track)
        tl.setContentsMargins(0, 0, 0, 0)
        fill = QFrame()
        fill.setObjectName("BarFill")
        frac = (seconds / maximum) if maximum > 0 else 0
        tl.addWidget(fill, max(1, int(frac * 1000)))
        tl.addStretch(max(1, int((1 - frac) * 1000)))
        lay.addWidget(track)


def ranking_list(items: list[Ranked], limit: int = 10) -> QWidget:
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6)
    top = items[:limit]
    maximum = top[0].seconds if top else 0
    for i, r in enumerate(top, 1):
        lay.addWidget(BarRow(f"{i}. {r.label}  ·  {r.sessions} sess.",
                             r.seconds, maximum))
    if not top:
        empty = QLabel("Sem atividade no período.")
        empty.setObjectName("CardMeta")
        lay.addWidget(empty)
    return box
