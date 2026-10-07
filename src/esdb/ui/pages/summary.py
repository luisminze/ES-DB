"""Página Resumo (painel inicial) — MAIN.md RF-04."""

from __future__ import annotations

from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QPushButton, QVBoxLayout,
                               QWidget)

from ...domain.calculations import Metrics, format_duration
from ..widgets import ranking_list, section_title, stat_tile
from .base import clear_layout, empty_label, scroll_container


class SummaryPage(QWidget):
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
            self._lay.addWidget(empty_label(
                "Configure o diretório do ES-DE em Configurações para começar."))
            self._lay.addStretch()
            return
        m: Metrics = lib.metrics(self._app.period)

        tiles = QGridLayout()
        tiles.setSpacing(12)
        data = [
            (format_duration(m.total_seconds), "Tempo jogado", True),
            (str(m.session_count), "Sessões", False),
            (format_duration(m.avg_session_seconds or 0), "Média por sessão", False),
            (str(m.games_played), "Jogos jogados", False),
            (str(m.platforms_played), "Plataformas", False),
            (str(m.longest_streak) + " dias", "Maior sequência", False),
        ]
        for i, (val, lab, acc) in enumerate(data):
            tiles.addWidget(stat_tile(val, lab, acc), i // 3, i % 3)
        self._lay.addLayout(tiles)

        highlights = QHBoxLayout()
        highlights.setSpacing(12)
        mg = m.most_played_game.label if m.most_played_game else "—"
        mp = m.most_played_platform.label if m.most_played_platform else "—"
        highlights.addWidget(stat_tile(mg, "Jogo mais jogado"))
        highlights.addWidget(stat_tile(mp, "Plataforma favorita"))
        self._lay.addLayout(highlights)

        self._lay.addWidget(section_title("Jogos mais jogados"))
        self._lay.addWidget(ranking_list(m.top_games, limit=5))

        self._lay.addWidget(section_title("Tempo por plataforma"))
        self._lay.addWidget(ranking_list(m.platform_distribution, limit=8))

        explore = QPushButton("Explorar biblioteca  →")
        explore.setObjectName("ChromeBtn")
        explore.clicked.connect(lambda: self._app.navigate("library"))
        row = QHBoxLayout()
        row.addWidget(explore)
        row.addStretch()
        self._lay.addLayout(row)
        self._lay.addStretch()
