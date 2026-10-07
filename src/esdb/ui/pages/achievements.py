"""Página Conquistas — RPCS3 · Xenia · shadPS4 (CONQUISTAS.md)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QScrollArea,
                               QVBoxLayout, QWidget)

from ...conquistas.models import GameAchievements
from ..widgets import cover_label, section_title, trophy_icon
from .base import clear_layout, empty_label

_GRADE_COLOR = {"platinum": "#8FB7D9", "gold": "#E6C04C", "silver": "#C7CCD1",
                "bronze": "#C98A5A", "gamerscore": "#6FB26F", "unknown": "#6B7280"}


class GameRow(QFrame):
    clicked = Signal(object)

    def __init__(self, game: GameAchievements, selected: bool) -> None:
        super().__init__()
        self.setObjectName("Card")
        self.setCursor(Qt.PointingHandCursor)
        self._game = game
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(10)
        if game.icon_path:
            lay.addWidget(cover_label(game.icon_path, game.title, 48, 48))
        col = QVBoxLayout()
        col.setSpacing(2)
        t = QLabel(game.title)
        t.setObjectName("CardTitle")
        t.setWordWrap(True)
        col.addWidget(t)
        if game.progress_available:
            meta = QLabel(f"{game.emulator} · {game.unlocked_count}/{game.total} "
                          f"· {game.percent:.0f}%")
        else:
            meta = QLabel(f"{game.emulator} · {game.total} troféus · progresso indisponível")
        meta.setObjectName("CardMeta")
        col.addWidget(meta)
        bar = QFrame()
        bar.setObjectName("Bar")
        bar.setFixedHeight(6)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(0, 0, 0, 0)
        fill = QFrame()
        fill.setObjectName("BarFill")
        pct = int(game.percent)
        bl.addWidget(fill, max(0, pct))
        bl.addStretch(max(1, 100 - pct))
        col.addWidget(bar)
        lay.addLayout(col, 1)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._game)
        super().mousePressEvent(event)


class AchievementsPage(QWidget):
    def __init__(self, app) -> None:
        super().__init__()
        self._app = app
        self._games: list[GameAchievements] = []
        self._selected: GameAchievements | None = None

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(14)

        left = QScrollArea()
        left.setWidgetResizable(True)
        left.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left.setFixedWidth(340)
        self._list_host = QWidget()
        self._list_host.setObjectName("ScrollBody")
        self._list_lay = QVBoxLayout(self._list_host)
        self._list_lay.setContentsMargins(2, 2, 8, 8)
        self._list_lay.setSpacing(8)
        left.setWidget(self._list_host)
        outer.addWidget(left)

        right = QScrollArea()
        right.setWidgetResizable(True)
        right.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._detail_host = QWidget()
        self._detail_host.setObjectName("ScrollBody")
        self._detail_lay = QVBoxLayout(self._detail_host)
        self._detail_lay.setContentsMargins(2, 2, 8, 8)
        self._detail_lay.setSpacing(8)
        right.setWidget(self._detail_host)
        outer.addWidget(right, 1)

    def update_view(self) -> None:
        self._games = self._app.conquistas_games()
        clear_layout(self._list_lay)
        if not self._games:
            self._list_lay.addWidget(empty_label(
                "Nenhum troféu encontrado. Configure as pastas dos emuladores "
                "em Configurações. Suportados: RPCS3, Xenia e shadPS4."))
            self._list_lay.addStretch()
            clear_layout(self._detail_lay)
            self._detail_lay.addStretch()
            return
        for g in self._games:
            row = GameRow(g, g is self._selected)
            row.clicked.connect(self._select)
            self._list_lay.addWidget(row)
        self._list_lay.addStretch()
        if self._selected not in self._games:
            self._selected = self._games[0]
        self._render_detail()

    def _select(self, game: GameAchievements) -> None:
        self._selected = game
        self._render_detail()

    def _render_detail(self) -> None:
        clear_layout(self._detail_lay)
        g = self._selected
        if g is None:
            self._detail_lay.addStretch()
            return
        head = QLabel(g.title)
        head.setObjectName("PageTitle")
        head.setWordWrap(True)
        self._detail_lay.addWidget(head)
        if g.progress_available:
            sub = QLabel(f"{g.emulator} · {g.unlocked_count} de {g.total} "
                         f"desbloqueados ({g.percent:.0f}%)")
        else:
            sub = QLabel(f"{g.emulator} · progresso indisponível — exibindo apenas "
                         f"as definições.")
        sub.setObjectName("PageSubtitle")
        self._detail_lay.addWidget(sub)

        if g.progress_available:
            unlocked = [a for a in g.achievements if a.unlocked]
            locked = [a for a in g.achievements if not a.unlocked]
            if unlocked:
                self._detail_lay.addWidget(
                    section_title(f"Desbloqueados ({len(unlocked)})"))
                for a in unlocked:
                    self._detail_lay.addWidget(self._trophy_row(a, True))
            if locked:
                self._detail_lay.addWidget(
                    section_title(f"Bloqueados ({len(locked)})"))
                for a in locked:
                    self._detail_lay.addWidget(self._trophy_row(a, True))
        else:
            for a in g.achievements:
                self._detail_lay.addWidget(self._trophy_row(a, False))
        self._detail_lay.addStretch()

    def _trophy_row(self, a, progress_available: bool) -> QFrame:
        card = QFrame()
        card.setObjectName("Tile")
        locked = progress_available and not a.unlocked
        lay = QHBoxLayout(card)
        lay.setContentsMargins(10, 6, 12, 6)
        lay.setSpacing(10)
        if a.icon_path and not (a.hidden and not a.unlocked):
            lay.addWidget(trophy_icon(a.icon_path, a.display_name(), 44,
                                      a.unlocked, a.grade.value))
        col = QVBoxLayout()
        col.setSpacing(2)
        name = QLabel(a.display_name())
        name.setObjectName("CardMeta" if locked else "CardTitle")
        if not locked:
            name.setStyleSheet("font-weight: 700;")
        name.setWordWrap(True)
        col.addWidget(name)
        desc = QLabel(a.display_description())
        desc.setObjectName("CardMeta")
        if locked:
            desc.setStyleSheet("color: #6B7280;")
        desc.setWordWrap(True)
        col.addWidget(desc)
        lay.addLayout(col, 1)

        meta = QVBoxLayout()
        meta.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        grade_text = (f"{a.gamerscore} G" if a.grade.value == "gamerscore"
                      and a.gamerscore else a.grade.label)
        grade = QLabel(grade_text)
        grade.setStyleSheet(f"color: {_GRADE_COLOR.get(a.grade.value, '#6B7280')};"
                            " font-weight: 700;")
        grade.setAlignment(Qt.AlignRight)
        meta.addWidget(grade)
        if not progress_available:
            state = QLabel("—")
        elif a.unlocked:
            when = a.unlocked_at.strftime("%d/%m/%Y") if a.unlocked_at else ""
            state = QLabel(f"✓ {when}".strip())
            state.setStyleSheet("color: #6FB26F;")
        else:
            state = QLabel("Bloqueado")
            state.setObjectName("CardMeta")
        state.setAlignment(Qt.AlignRight)
        meta.addWidget(state)
        lay.addLayout(meta)
        return card
