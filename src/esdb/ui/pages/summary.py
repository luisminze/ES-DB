"""Página Resumo — visão agregada (ES-DB-Update1).

Engloba os dados das abas Estatísticas, Conquistas e Retrospectiva num único
painel de visão geral, respeitando o período selecionado para a parte analítica.
"""

from __future__ import annotations

from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QPushButton, QVBoxLayout, QWidget)

from ...conquistas.scoring import (achievement_stats, sony_score,
                                   xbox_gamerscore)
from ...domain.calculations import Metrics, format_duration
from ...domain.periods import year_period
from ...domain.year_review import available_years, compute_year_review
from ..charts import SEGMENT_COLORS, RingChart
from ..widgets import cover_fit_label, ranking_list, section_title, stat_tile
from .base import clear_layout, empty_label, scroll_container

_PLATFORM_COLOR = {"RPCS3": "#4A90D9", "Xenia": "#4FB15A", "shadPS4": "#7C5CCB"}


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
        self._section_stats(lib.metrics(self._app.period))
        self._section_conquistas()
        self._section_retrospectiva()
        self._lay.addStretch()

    # ---------------------------------------------------------- estatísticas
    def _section_stats(self, m: Metrics) -> None:
        self._lay.addWidget(section_title("Estatísticas"))
        tiles = QGridLayout()
        tiles.setSpacing(12)
        data = [
            (format_duration(m.total_seconds), "Tempo jogado", True),
            (str(m.session_count), "Sessões", False),
            (format_duration(m.avg_session_seconds or 0), "Média por sessão", False),
            (str(m.games_played), "Jogos jogados", False),
            (str(m.platforms_played), "Plataformas", False),
            (f"{m.longest_streak} dias", "Maior sequência", False),
        ]
        for i, (v, lab, acc) in enumerate(data):
            tiles.addWidget(stat_tile(v, lab, acc), i // 3, i % 3)
        self._lay.addLayout(tiles)

        cols = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(section_title("Jogos mais jogados"))
        left.addWidget(ranking_list(m.top_games, limit=5))
        right = QVBoxLayout()
        right.addWidget(section_title("Tempo por plataforma"))
        right.addWidget(ranking_list(m.platform_distribution, limit=5))
        lw, rw = QWidget(), QWidget()
        lw.setLayout(left); rw.setLayout(right)
        cols.addWidget(lw, 1); cols.addWidget(rw, 1)
        self._lay.addLayout(cols)

    # ----------------------------------------------------------- conquistas
    def _section_conquistas(self) -> None:
        games = self._app.conquistas_games()
        if not games:
            return
        self._lay.addWidget(section_title("Conquistas"))
        stats = achievement_stats(games)
        sony = sony_score(games)
        gs = xbox_gamerscore(games)

        score = QHBoxLayout()
        score.setSpacing(12)
        score.addWidget(stat_tile(f"{sony.points} pts", f"Nível {sony.category} (Sony)", True))
        score.addWidget(stat_tile(f"{gs} G", "Gamerscore (Xbox)"))
        score.addWidget(stat_tile(f"{stats.unlocked}/{stats.total}", "Desbloqueadas"))
        self._lay.addLayout(score)

        rings = QFrame()
        rings.setObjectName("RetroCard")
        rl = QHBoxLayout(rings)
        rl.setContentsMargins(14, 10, 14, 10)
        rl.setSpacing(8)
        comp = int(round(stats.completed_pct))
        rl.addWidget(RingChart("Jogos 100%", [("#EB5E54", comp), ("#2A2E38", 100 - comp)],
                               f"{comp}%", f"{stats.completed_games}/{stats.total_games}"))
        plat = [(_PLATFORM_COLOR.get(e, SEGMENT_COLORS[i % len(SEGMENT_COLORS)]), v)
                for i, (e, v) in enumerate(sorted(stats.by_platform.items()))]
        rl.addWidget(RingChart("Por plataforma", plat or [("#2A2E38", 1)],
                               str(stats.unlocked), "desbloq."))
        rare_pct = int(round(100 * stats.rare_unlocked / stats.unlocked)) if stats.unlocked else 0
        rl.addWidget(RingChart("Raras", [("#E6C04C", stats.rare_unlocked),
                                         ("#2A2E38", max(0, stats.unlocked - stats.rare_unlocked))],
                               str(stats.rare_unlocked), f"{rare_pct}%"))
        self._lay.addWidget(rings)

    # -------------------------------------------------------- retrospectiva
    def _section_retrospectiva(self) -> None:
        lib = self._app.library
        years = available_years(lib.sessions, self._app.tz)
        if not years:
            return
        year = years[0]
        r = compute_year_review(lib.sessions, lib.games_by_id, year, self._app.tz)
        if not r.has_data:
            return
        self._lay.addWidget(section_title(f"Retrospectiva {year}"))
        banner = QFrame()
        banner.setObjectName("RetroCard")
        row = QHBoxLayout(banner)
        row.setContentsMargins(20, 14, 20, 14)
        row.setSpacing(22)
        m = r.metrics
        for value, label in (
            (str(m.games_played), "Jogos jogados"),
            (str(m.session_count), "Sessões"),
            (format_duration(m.total_seconds), "Tempo total"),
            (f"{m.longest_streak} dias", "Maior sequência"),
        ):
            box = QVBoxLayout()
            num = QLabel(value)
            num.setObjectName("BannerNum")
            lab = QLabel(label)
            lab.setObjectName("CardMeta")
            box.addWidget(num)
            box.addWidget(lab)
            holder = QWidget()
            holder.setLayout(box)
            row.addWidget(holder, 1)
        self._lay.addWidget(banner)

        covers = QHBoxLayout()
        covers.setSpacing(12)
        for ranked in m.top_games[:5]:
            g = lib.games_by_id.get(ranked.key)
            covers.addWidget(cover_fit_label(g.cover_path if g else None,
                                             ranked.label, 92))
        covers.addStretch()
        holder = QWidget()
        holder.setLayout(covers)
        self._lay.addWidget(holder)

        btn = QPushButton("Ver retrospectiva completa  →")
        btn.setObjectName("ChromeBtn")
        btn.clicked.connect(lambda: self._app.navigate("retrospective"))
        brow = QHBoxLayout()
        brow.addWidget(btn)
        brow.addStretch()
        self._lay.addLayout(brow)
