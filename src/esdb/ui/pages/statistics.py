"""Página Estatísticas — MAIN.md RF-06A, DESIGN.md §7."""

from __future__ import annotations

from datetime import timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ...domain.calculations import Metrics, format_duration
from ..widgets import ranking_list, section_title, stat_tile
from .base import clear_layout, empty_label, scroll_container


class StatisticsPage(QWidget):
    def __init__(self, app) -> None:
        super().__init__()
        self._app = app
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._area, self._content, self._lay = scroll_container()
        outer.addWidget(self._area)

    def update_view(self) -> None:
        clear_layout(self._lay)
        lib = self._app.library
        if lib is None:
            self._lay.addWidget(empty_label("Sem fonte configurada."))
            self._lay.addStretch()
            return
        m: Metrics = lib.metrics(self._app.period)
        if m.total_seconds <= 0:
            self._lay.addWidget(empty_label(
                "Sem sessões no período selecionado. Ajuste o período acima."))
            self._lay.addStretch()
            return

        tiles = QGridLayout()
        tiles.setSpacing(12)
        data = [
            (format_duration(m.total_seconds), "Tempo jogado", True),
            (str(m.session_count), "Sessões", False),
            (format_duration(m.avg_session_seconds or 0), "Média por sessão", False),
            (str(m.games_played), "Jogos jogados", False),
            (str(m.platforms_played), "Plataformas", False),
        ]
        for i, (val, lab, acc) in enumerate(data):
            tiles.addWidget(stat_tile(val, lab, acc), 0, i)
        self._lay.addLayout(tiles)

        self._lay.addWidget(section_title("Atividade por dia"))
        self._lay.addWidget(self._daily_chart(m))

        cols = QHBoxLayout()
        cols.setSpacing(16)
        left = QVBoxLayout()
        left.addWidget(section_title("Jogos mais jogados"))
        left.addWidget(ranking_list(m.top_games, limit=10))
        right = QVBoxLayout()
        right.addWidget(section_title("Tempo por plataforma"))
        right.addWidget(ranking_list(m.platform_distribution, limit=10))
        lw, rw = QWidget(), QWidget()
        lw.setLayout(left)
        rw.setLayout(right)
        cols.addWidget(lw, 1)
        cols.addWidget(rw, 1)
        self._lay.addLayout(cols)

        habits = QHBoxLayout()
        habits.setSpacing(12)
        day = (m.most_active_day[0].strftime("%d/%m/%Y")
               if m.most_active_day else "—")
        last = m.last_session_at.strftime("%d/%m/%Y %H:%M") if m.last_session_at else "—"
        habits.addWidget(stat_tile(day, "Dia mais ativo"))
        habits.addWidget(stat_tile(f"{m.longest_streak} dias", "Maior sequência"))
        habits.addWidget(stat_tile(last, "Última sessão"))
        self._lay.addLayout(habits)
        self._lay.addStretch()

    def _daily_chart(self, m: Metrics) -> QWidget:
        box = QFrame()
        box.setObjectName("Tile")
        box.setMinimumHeight(170)
        lay = QHBoxLayout(box)
        lay.setContentsMargins(16, 16, 16, 10)
        lay.setSpacing(4)
        lay.setAlignment(Qt.AlignBottom)
        if not m.daily_activity:
            return empty_label("Sem dados diários.")
        days = sorted(m.daily_activity)
        # limita a no máximo ~60 colunas mais recentes para legibilidade
        days = days[-60:]
        maximum = max(m.daily_activity[d] for d in days) or 1
        for d in days:
            secs = m.daily_activity[d]
            col = QVBoxLayout()
            col.setAlignment(Qt.AlignBottom)
            bar = QFrame()
            bar.setObjectName("BarFill")
            height = max(3, int(120 * secs / maximum))
            bar.setFixedHeight(height)
            bar.setFixedWidth(max(4, min(16, 900 // max(1, len(days)))))
            bar.setToolTip(f"{d.strftime('%d/%m/%Y')}: {format_duration(secs)}")
            col.addWidget(bar)
            wrap = QWidget()
            wrap.setLayout(col)
            lay.addWidget(wrap)
        return box
