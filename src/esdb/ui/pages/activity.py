"""Página Atividade — feed pessoal + sessões (ATIVIDADE.md)."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel,
                               QPushButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from ...domain.calculations import format_duration
from ...domain.models import DurationKind
from ..widgets import cover_label
from .base import clear_layout, empty_label, scroll_container

MILESTONES_H = [1, 5, 10, 25, 50, 100, 250, 500, 1000]
_MONTHS = ["", "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
           "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]


class ActivityPage(QWidget):
    def __init__(self, app) -> None:
        super().__init__()
        self._app = app
        self._mode = "feed"
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)

        toggle = QHBoxLayout()
        self._group = QButtonGroup(self)
        for key, label in (("feed", "Feed"), ("sessions", "Sessões")):
            btn = QPushButton(label)
            btn.setObjectName("ChromeBtn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _=False, k=key: self._set_mode(k))
            self._group.addButton(btn)
            toggle.addWidget(btn)
            if key == "feed":
                btn.setChecked(True)
        toggle.addStretch()
        outer.addLayout(toggle)

        self._area, self._content, self._lay = scroll_container()
        outer.addWidget(self._area)

    def _set_mode(self, mode: str) -> None:
        self._mode = mode
        self.update_view()

    def update_view(self) -> None:
        clear_layout(self._lay)
        lib = self._app.library
        if lib is None:
            self._lay.addWidget(empty_label("Sem fonte configurada."))
            self._lay.addStretch()
            return
        if self._mode == "feed":
            self._build_feed()
        else:
            self._build_sessions()

    # ------------------------------------------------------------- feed
    def _build_feed(self) -> None:
        events = self._feed_events()
        if not events:
            self._lay.addWidget(empty_label("Sem atividade registrada ainda."))
            self._lay.addStretch()
            return
        current_month = None
        for ev in events:
            ym = (ev["when"].year, ev["when"].month)
            if ym != current_month:
                current_month = ym
                div = QLabel(f"{_MONTHS[ym[1]]} DE {ym[0]}")
                div.setObjectName("Divider")
                self._lay.addWidget(div)
            self._lay.addWidget(self._event_widget(ev))
        self._lay.addStretch()

    def _event_widget(self, ev: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("Card" if ev["big"] else "Tile")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(12)
        if ev["big"] and ev.get("game"):
            lay.addWidget(cover_label(ev["game"].cover_path,
                                      ev["game"].display_title, 60, 90))
        text = QVBoxLayout()
        title = QLabel(ev["title"])
        title.setObjectName("CardTitle")
        title.setWordWrap(True)
        when = QLabel(ev["when"].strftime("%d/%m/%Y %H:%M"))
        when.setObjectName("CardMeta")
        text.addWidget(title)
        text.addWidget(when)
        lay.addLayout(text, 1)
        return card

    def _feed_events(self) -> list[dict]:
        lib = self._app.library
        valid = sorted((s for s in lib.sessions if s.is_valid),
                       key=lambda s: s.started_at)
        events: list[dict] = []
        seen_games: set[int] = set()
        seen_platforms: set[str] = set()
        cumulative: dict[int, int] = defaultdict(int)
        milestone_hit: set[tuple[int, int]] = set()
        daily: dict = defaultdict(lambda: {"secs": 0, "games": set(), "when": None})

        for s in valid:
            g = lib.games_by_id.get(s.game_id)
            if g is None:
                continue
            if s.game_id not in seen_games:
                seen_games.add(s.game_id)
                events.append({"when": s.started_at, "big": True, "game": g,
                               "title": f"Você jogou {g.display_title} pela primeira vez."})
            if g.platform and g.platform not in seen_platforms:
                seen_platforms.add(g.platform)
                events.append({"when": s.started_at, "big": False, "game": g,
                               "title": f"Primeira vez em {g.platform}."})
            before = cumulative[s.game_id]
            cumulative[s.game_id] += s.duration_seconds
            after = cumulative[s.game_id]
            for h in MILESTONES_H:
                thr = h * 3600
                if before < thr <= after and (s.game_id, h) not in milestone_hit:
                    milestone_hit.add((s.game_id, h))
                    events.append({"when": s.ended_at, "big": True, "game": g,
                                   "title": f"Você alcançou {h} h em {g.display_title}."})
            d = s.started_at.astimezone(self._app.tz).date()
            daily[d]["secs"] += s.duration_seconds
            daily[d]["games"].add(s.game_id)
            daily[d]["when"] = s.ended_at

        for d, agg in daily.items():
            events.append({"when": agg["when"], "big": False, "game": None,
                           "title": f"Você jogou {format_duration(agg['secs'])} "
                                    f"em {len(agg['games'])} jogo(s)."})
        events.sort(key=lambda e: e["when"], reverse=True)
        return events

    # --------------------------------------------------------- sessions
    def _build_sessions(self) -> None:
        lib = self._app.library
        rows = sorted(lib.sessions, key=lambda s: s.started_at, reverse=True)
        table = QTableWidget(len(rows), 4)
        table.setHorizontalHeaderLabels(["Início", "Jogo", "Plataforma", "Duração"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        table.setColumnWidth(0, 160)
        table.setColumnWidth(1, 280)
        table.setColumnWidth(2, 200)
        for r, s in enumerate(rows):
            g = lib.games_by_id.get(s.game_id)
            kind = "" if s.is_valid else f" ({s.kind.value})"
            table.setItem(r, 0, QTableWidgetItem(
                s.started_at.astimezone(self._app.tz).strftime("%d/%m/%Y %H:%M")))
            table.setItem(r, 1, QTableWidgetItem(g.display_title if g else "—"))
            table.setItem(r, 2, QTableWidgetItem(g.platform if g else "—"))
            table.setItem(r, 3, QTableWidgetItem(format_duration(s.duration_seconds) + kind))
        self._lay.addWidget(table)
