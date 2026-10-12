"""Página Biblioteca — grade de capas com painel de plataformas e controles.

Barra de controles (Organizar / Agrupar / Visualização) + painel lateral de
Plataformas que filtra rapidamente, inspirado no mock de Update (DESIGN.md §5).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QFrame,
                               QGridLayout, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from ...domain.calculations import format_duration
from ...domain.models import Game
from ..widgets import cover_fit_label
from .base import clear_layout, empty_label

COVER_W, COVER_H = 150, 225
CARD_W = COVER_W + 24

# Organizar: rótulo → chave de ordenação
SORTS = [
    ("Mais jogado", "played"),
    ("Alfabético", "alpha"),
    ("Plataforma", "platform"),
    ("Gênero", "genre"),
    ("Sessões", "sessions"),
]


def _sort_games(games: list[Game], key: str) -> list[Game]:
    if key == "alpha":
        return sorted(games, key=lambda g: g.display_title.lower())
    if key == "platform":
        return sorted(games, key=lambda g: (g.platform.lower(),
                                            -g.total_seconds))
    if key == "genre":
        return sorted(games, key=lambda g: (
            (g.metadata.genre if g.metadata and g.metadata.genre else "~").lower(),
            -g.total_seconds))
    if key == "sessions":
        return sorted(games, key=lambda g: g.session_count, reverse=True)
    return sorted(games, key=lambda g: g.total_seconds, reverse=True)


def _group_key(game: Game, by: str) -> str:
    if by == "genre":
        return (game.metadata.genre if game.metadata and game.metadata.genre
                else "Sem gênero")
    return game.platform or "Sem plataforma"


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
        lay.addWidget(cover_fit_label(game.cover_path, game.display_title,
                                      COVER_W), 0, Qt.AlignHCenter)
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
        self._sort = "played"
        self._group = False
        self._carousel = False
        self._panel_visible = True
        self._games: list[Game] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)
        outer.addLayout(self._build_toolbar())

        body = QHBoxLayout()
        body.setSpacing(12)
        self._panel = self._build_platform_panel()
        body.addWidget(self._panel)

        self._area = QScrollArea()
        self._area.setWidgetResizable(True)
        self._area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._host = QWidget()
        self._host.setObjectName("ScrollBody")
        self._body = QVBoxLayout(self._host)
        self._body.setSpacing(16)
        self._body.setContentsMargins(4, 4, 8, 8)
        self._body.setAlignment(Qt.AlignTop)
        self._area.setWidget(self._host)
        body.addWidget(self._area, 1)
        outer.addLayout(body, 1)

    # ----------------------------------------------------------- toolbar
    def _build_toolbar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(8)
        self._panel_btn = QPushButton("Plataformas")
        self._panel_btn.setObjectName("ChromeBtn")
        self._panel_btn.setCheckable(True)
        self._panel_btn.setChecked(True)
        self._panel_btn.toggled.connect(self._toggle_panel)
        bar.addWidget(self._panel_btn)

        self._header = QLabel()
        self._header.setObjectName("PageSubtitle")
        bar.addWidget(self._header)
        bar.addStretch(1)

        bar.addWidget(QLabel("Organizar:"))
        self._sort_combo = QComboBox()
        for label, key in SORTS:
            self._sort_combo.addItem(label, key)
        self._sort_combo.currentIndexChanged.connect(self._on_sort)
        bar.addWidget(self._sort_combo)

        self._group_chk = QCheckBox("Agrupar")
        self._group_chk.toggled.connect(self._on_group)
        bar.addWidget(self._group_chk)

        bar.addWidget(QLabel("Visualização:"))
        self._view_combo = QComboBox()
        self._view_combo.addItem("Grade", False)
        self._view_combo.addItem("Carrossel", True)
        self._view_combo.currentIndexChanged.connect(self._on_view)
        bar.addWidget(self._view_combo)
        return bar

    def _build_platform_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("SidePanel")
        panel.setFixedWidth(210)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(10, 12, 10, 12)
        lay.setSpacing(2)
        title = QLabel("PLATAFORMAS")
        title.setObjectName("SideTitle")
        lay.addWidget(title)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area.setFrameShape(QFrame.NoFrame)
        self._plat_host = QWidget()
        self._plat_host.setObjectName("ScrollBody")
        self._plat_lay = QVBoxLayout(self._plat_host)
        self._plat_lay.setContentsMargins(0, 0, 0, 0)
        self._plat_lay.setSpacing(2)
        self._plat_lay.setAlignment(Qt.AlignTop)
        area.setWidget(self._plat_host)
        lay.addWidget(area, 1)
        self._plat_group = QButtonGroup(self)
        self._plat_group.setExclusive(True)
        return panel

    def _populate_platforms(self) -> None:
        clear_layout(self._plat_lay)
        for btn in list(self._plat_group.buttons()):
            self._plat_group.removeButton(btn)
        lib = self._app.library
        plats = lib.platforms if lib else []
        selected = self._app.filters["platforms"]
        current = next(iter(selected)) if len(selected) == 1 else None
        rows = [("Todas as plataformas", None)] + [(p, p) for p in plats]
        for label, value in rows:
            btn = QPushButton(label)
            btn.setObjectName("SideItem")
            btn.setCheckable(True)
            btn.setChecked(value == current or (value is None and current is None))
            btn.clicked.connect(lambda _=False, v=value: self._pick_platform(v))
            self._plat_group.addButton(btn)
            self._plat_lay.addWidget(btn)
        self._plat_lay.addStretch()

    def _pick_platform(self, value) -> None:
        self._app.filters["platforms"] = set() if value is None else {value}
        self.update_view()

    # ----------------------------------------------------------- actions
    def _toggle_panel(self, checked: bool) -> None:
        self._panel_visible = checked
        self._panel.setVisible(checked)

    def _on_sort(self, _i: int) -> None:
        self._sort = self._sort_combo.currentData()
        self._relayout()

    def _on_group(self, checked: bool) -> None:
        self._group = checked
        self._relayout()

    def _on_view(self, _i: int) -> None:
        self._carousel = bool(self._view_combo.currentData())
        self._relayout()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if not self._carousel:
            self._relayout()

    # ------------------------------------------------------------ render
    def update_view(self) -> None:
        lib = self._app.library
        if lib is None:
            clear_layout(self._body)
            self._header.setText("Sem fonte configurada.")
            return
        self._populate_platforms()
        self._games = self._app.filtered_games()
        total = sum(g.total_seconds for g in self._games)
        self._header.setText(
            f"{self._app.library_scope_label()} · {len(self._games)} jogos · "
            f"{format_duration(total)}")
        self._relayout()

    def _cols(self) -> int:
        width = self._area.viewport().width()
        return max(1, (width - 20) // (CARD_W + 20)) if width > 1 else self._columns

    def _relayout(self) -> None:
        clear_layout(self._body)
        if not self._games:
            self._body.addWidget(empty_label(
                "Nenhum jogo corresponde aos filtros atuais."))
            return
        games = _sort_games(self._games, self._sort)
        if self._group or self._carousel:
            group_by = "genre" if self._sort == "genre" else "platform"
            groups: dict[str, list[Game]] = {}
            for g in games:
                groups.setdefault(_group_key(g, group_by), []).append(g)
            for name in sorted(groups):
                header = QLabel(f"{name}  ({len(groups[name])})")
                header.setObjectName("GroupHeader")
                self._body.addWidget(header)
                if self._carousel:
                    self._body.addWidget(self._carousel_strip(groups[name]))
                else:
                    self._body.addWidget(self._grid_of(groups[name]))
        else:
            self._body.addWidget(self._grid_of(games))

    def _grid_of(self, games: list[Game]) -> QWidget:
        host = QWidget()
        host.setObjectName("ScrollBody")
        grid = QGridLayout(host)
        grid.setSpacing(20)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        cols = self._cols()
        self._columns = cols
        for idx, game in enumerate(games):
            card = GameCard(game)
            card.clicked.connect(self._app.open_game)
            grid.addWidget(card, idx // cols, idx % cols)
        return host

    def _carousel_strip(self, games: list[Game]) -> QWidget:
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFixedHeight(320)
        area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        host = QWidget()
        host.setObjectName("ScrollBody")
        row = QHBoxLayout(host)
        row.setContentsMargins(0, 0, 0, 8)
        row.setSpacing(16)
        row.setAlignment(Qt.AlignLeft)
        for game in games:
            card = GameCard(game)
            card.clicked.connect(self._app.open_game)
            row.addWidget(card)
        row.addStretch()
        area.setWidget(host)
        return area
