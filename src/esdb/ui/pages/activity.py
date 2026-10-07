"""Página Atividade — feed pessoal + sessões (ATIVIDADE.md)."""

from __future__ import annotations

import os
import re
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
    @staticmethod
    def _norm(title: str) -> str:
        """Normaliza um título para casar jogo de sessão com jogo de conquista."""
        t = re.sub(r"[™®©]", "", title or "")
        t = re.sub(r"[^0-9a-zA-Z]+", "", t)
        return t.casefold()

    def _build_feed(self) -> None:
        groups = self._feed_groups()
        if not groups:
            self._lay.addWidget(empty_label("Sem atividade registrada ainda."))
            self._lay.addStretch()
            return
        current_month = None
        for g in groups:
            ym = (g["when"].year, g["when"].month)
            if ym != current_month:
                current_month = ym
                div = QLabel(f"{_MONTHS[ym[1]]} DE {ym[0]}")
                div.setObjectName("Divider")
                self._lay.addWidget(div)
            self._lay.addWidget(self._group_widget(g))
        self._lay.addStretch()

    def _group_widget(self, g: dict) -> QFrame:
        """Um card por jogo/dia, com tudo que aconteceu (Update2)."""
        card = QFrame()
        card.setObjectName("Card")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(12)
        if g.get("cover"):
            size = (60, 90) if g.get("is_lib") else (52, 52)
            lay.addWidget(cover_label(g["cover"], g["title"], *size), 0, Qt.AlignTop)

        text = QVBoxLayout()
        text.setSpacing(2)
        head = QHBoxLayout()
        title = QLabel(g["title"])
        title.setObjectName("CardTitle")
        title.setWordWrap(True)
        date = QLabel(g["date"].strftime("%d/%m/%Y"))
        date.setObjectName("CardMeta")
        date.setAlignment(Qt.AlignRight | Qt.AlignTop)
        head.addWidget(title, 1)
        head.addWidget(date)
        text.addLayout(head)

        for line in self._group_lines(g):
            lab = QLabel(line)
            lab.setObjectName("CardMeta")
            lab.setWordWrap(True)
            text.addWidget(lab)
        lay.addLayout(text, 1)
        return card

    @staticmethod
    def _group_lines(g: dict) -> list[str]:
        lines: list[str] = []
        if g["secs"] > 0:
            extra = " · primeira vez jogando" if g["first_play"] else ""
            lines.append(f"🎮 Jogou {format_duration(g['secs'])}{extra}")
        for h in sorted(g["milestones"]):
            lines.append(f"🏅 Alcançou {h} h de jogo")
        for name, grade in g["achievements"][:8]:
            lines.append(f"🏆 Desbloqueou \"{name}\" ({grade})")
        if len(g["achievements"]) > 8:
            lines.append(f"🏆 +{len(g['achievements']) - 8} conquistas")
        if g["screenshots"] > 0:
            lines.append(f"📷 {g['screenshots']} screenshot(s)")
        return lines

    def _feed_groups(self) -> list[dict]:
        lib = self._app.library
        tz = self._app.tz
        groups: dict[tuple, dict] = {}

        def grp(key, date, title, cover, is_lib) -> dict:
            k = (key, date)
            g = groups.get(k)
            if g is None:
                g = {"date": date, "title": title, "cover": cover,
                     "is_lib": is_lib, "secs": 0, "first_play": False,
                     "milestones": [], "achievements": [], "screenshots": 0,
                     "when": datetime.combine(date, datetime.min.time(), tzinfo=tz)}
                groups[k] = g
            return g

        def touch(g, when):
            if when > g["when"]:
                g["when"] = when

        valid = sorted((s for s in lib.sessions if s.is_valid),
                       key=lambda s: s.started_at)
        seen_games: set[int] = set()
        cumulative: dict[int, int] = defaultdict(int)
        milestone_hit: set[tuple[int, int]] = set()
        for s in valid:
            game = lib.games_by_id.get(s.game_id)
            if game is None:
                continue
            d = s.started_at.astimezone(tz).date()
            g = grp(("lib", s.game_id), d, game.display_title, game.cover_path, True)
            g["secs"] += s.duration_seconds
            touch(g, s.ended_at)
            if s.game_id not in seen_games:
                seen_games.add(s.game_id)
                g["first_play"] = True
            before = cumulative[s.game_id]
            cumulative[s.game_id] += s.duration_seconds
            after = cumulative[s.game_id]
            for h in MILESTONES_H:
                thr = h * 3600
                if before < thr <= after and (s.game_id, h) not in milestone_hit:
                    milestone_hit.add((s.game_id, h))
                    g["milestones"].append(h)

        # Conquistas: casa com o jogo da biblioteca por título normalizado.
        norm_map = {self._norm(gm.display_title): gid
                    for gid, gm in lib.games_by_id.items()}
        for ga in self._app.conquistas_games():
            lib_gid = norm_map.get(self._norm(ga.title))
            for a in ga.achievements:
                if not (a.unlocked and a.unlocked_at):
                    continue
                when = a.unlocked_at
                if when.tzinfo is None:
                    when = when.replace(tzinfo=tz)
                d = when.astimezone(tz).date()
                if lib_gid is not None:
                    game = lib.games_by_id[lib_gid]
                    g = grp(("lib", lib_gid), d, game.display_title,
                            game.cover_path, True)
                else:
                    g = grp(("ach", ga.comm_id), d, ga.title,
                            a.icon_path or ga.icon_path, False)
                g["achievements"].append((a.name, a.grade.label))
                touch(g, when)

        # Screenshots: data pela modificação do arquivo (melhor-esforço).
        for gid, game in lib.games_by_id.items():
            for path in lib.screenshots_for(game):
                try:
                    mt = datetime.fromtimestamp(os.path.getmtime(path), tz)
                except OSError:
                    continue
                g = grp(("lib", gid), mt.date(), game.display_title,
                        game.cover_path, True)
                g["screenshots"] += 1
                touch(g, mt)

        return sorted(groups.values(), key=lambda g: g["when"], reverse=True)

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
