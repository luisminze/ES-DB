"""Gráficos de anel (donut) reutilizáveis — aba Conquistas (ES-DB-Update1).

Mantêm a identidade do ES-DB (carvão + acento vermelho); sem rede.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QVBoxLayout, QWidget

# Paleta categórica usada nos segmentos (cores distintas, coerentes com o tema).
SEGMENT_COLORS = ["#EB5E54", "#E0A24A", "#4FB15A", "#3BA7AD", "#4A90D9",
                  "#7C5CCB", "#C06BB0", "#7E8CA0"]
_TRACK = "#2A2E38"


class RingChart(QWidget):
    """Anel com segmentos proporcionais e rótulo central."""

    def __init__(self, title: str, segments: list[tuple[str, float]],
                 center_value: str, center_label: str = "") -> None:
        super().__init__()
        self._title = title
        self._segments = [(c, v) for c, v in segments if v > 0]
        self._center_value = center_value
        self._center_label = center_label
        self.setMinimumSize(150, 180)

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        p.setPen(QColor("#9BA1AD"))
        tf = QFont(p.font()); tf.setPointSize(9); tf.setBold(True)
        p.setFont(tf)
        p.drawText(QRectF(0, 4, w, 18), Qt.AlignHCenter, self._title)

        top = 26
        side = min(w, h - top) - 12
        cx = (w - side) / 2
        cy = top + (h - top - side) / 2
        rect = QRectF(cx, cy, side, side)
        thickness = max(10, side * 0.16)
        pen = QPen()
        pen.setWidthF(thickness)
        pen.setCapStyle(Qt.FlatCap)

        pen.setColor(QColor(_TRACK))
        p.setPen(pen)
        p.drawArc(rect.adjusted(thickness / 2, thickness / 2,
                                -thickness / 2, -thickness / 2),
                  0, 360 * 16)

        total = sum(v for _, v in self._segments) or 1.0
        start = 90 * 16  # topo
        for color, value in self._segments:
            span = -int(360 * 16 * value / total)
            pen.setColor(QColor(color))
            p.setPen(pen)
            p.drawArc(rect.adjusted(thickness / 2, thickness / 2,
                                    -thickness / 2, -thickness / 2),
                      start, span)
            start += span

        p.setPen(QColor("#FFFFFF"))
        vf = QFont(p.font()); vf.setPointSize(16); vf.setBold(True)
        p.setFont(vf)
        p.drawText(rect, Qt.AlignCenter, self._center_value)
        if self._center_label:
            p.setPen(QColor("#9BA1AD"))
            lf = QFont(p.font()); lf.setPointSize(8); lf.setBold(False)
            p.setFont(lf)
            p.drawText(QRectF(cx, cy + side / 2 + 8, side, 16),
                       Qt.AlignHCenter, self._center_label)


def legend_row(items: list[tuple[str, str]]) -> QWidget:
    """Legenda simples: lista de (cor, rótulo)."""
    from PySide6.QtWidgets import QHBoxLayout, QLabel
    host = QWidget()
    lay = QHBoxLayout(host)
    lay.setContentsMargins(0, 2, 0, 0)
    lay.setSpacing(12)
    lay.addStretch()
    for color, label in items:
        chip = QWidget()
        h = QHBoxLayout(chip)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(5)
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {color}; font-size: 12px;")
        txt = QLabel(label)
        txt.setObjectName("CardMeta")
        h.addWidget(dot)
        h.addWidget(txt)
        lay.addWidget(chip)
    lay.addStretch()
    return host
