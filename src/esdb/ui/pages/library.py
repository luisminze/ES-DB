"""Página Biblioteca — grade de capas (DESIGN.md §5)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFrame, QGridLayout, QLabel, QScrollArea,
                               QVBoxLayout, QWidget)

from ...domain.calculations import format_duration
from ...domain.models import Game
from ..widgets import cover_label
from .base import clear_layout, empty_label

COVER_W, COVER_H = 150, 225
CARD_W = COVER_W + 24


class GameCard(QFrame):
    clicked = Signal(object)

    def __init__(self, game: Game) -> None:
        super().__init__()
        self.setObjectName("Card")
        self.setFixedWidth(CARD_W)
        self.setCursor(Qt.PointingHandCursor)
        self._game = game
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(6)
        lay.addWidget(cover_label(game.cover_path, game.display_title,
                                  COVER_W, COVER_H), 0, Qt.AlignHCenter)
        title = QLabel(game.display_title)
        title.setObjectName("CardTitle")
        title.setWordWrap(True)
        title.setMaximumHeight(40)
        lay.addWidget(title)
        meta = QLabel(game.platform)
        meta.setObjectName("CardMeta")
        meta.setWordWrap(True)
        lay.addWidget(meta)
        stats = QLabel(f"{format_duration(game.total_seconds)} · "
                       f"{game.session_count} sess.")
        stats.setObjectName("CardMeta")
        lay.addWidget(stats)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._game)
        super().mousePressEvent(event)


class LibraryPage(QWidget):
    def __init__(self, app) -> None:
        super().__init__()
        self._app = app
        self._columns = 4
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)
        self._header = QLabel()
        self._header.setObjectName("PageSubtitle")
        outer.addWidget(self._header)
        self._area = QScrollArea()
        self._area.setWidgetResizable(True)
        self._area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._grid_host = QWidget()
        self._grid_host.setObjectName("ScrollBody")
        self._grid = QGridLayout(self._grid_host)
        self._grid.setSpacing(20)
        self._grid.setContentsMargins(4, 4, 8, 8)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._area.setWidget(self._grid_host)
        outer.addWidget(self._area)
        self._games: list[Game] = []

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        width = self._area.viewport().width()
        cols = max(1, (width - 20) // (CARD_W + 20))
        if cols != self._columns:
            self._columns = cols
            self._relayout()

    def update_view(self) -> None:
        lib = self._app.library
        if lib is None:
            clear_layout(self._grid)
            self._header.setText("Sem fonte configurada.")
            return
        self._games = self._app.filtered_games()
        total = sum(g.total_seconds for g in self._games)
        self._header.setText(
            f"{self._app.library_scope_label()} · {len(self._games)} jogos · "
            f"{format_duration(total)}")
        self._relayout()

    def _relayout(self) -> None:
        clear_layout(self._grid)
        width = self._area.viewport().width()
        if width > 1:
            self._columns = max(1, (width - 20) // (CARD_W + 20))
        if not self._games:
            self._grid.addWidget(empty_label(
                "Nenhum jogo corresponde aos filtros atuais."), 0, 0)
            return
        for idx, game in enumerate(self._games):
            card = GameCard(game)
            card.clicked.connect(self._app.open_game)
            self._grid.addWidget(card, idx // self._columns, idx % self._columns)
