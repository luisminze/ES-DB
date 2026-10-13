"""Agregados (distribuição) de conquistas para os anéis da aba Conquistas.

Sem sistema de pontuação/níveis — apenas contagens de progresso por jogo,
plataforma e grau de troféu. Tudo calculado localmente (sem rede).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import GameAchievements, Grade


@dataclass(slots=True)
class AchievementStats:
    """Agregados para os anéis da aba Conquistas (ES-DB-Update1)."""

    total_games: int = 0
    completed_games: int = 0            # 100% desbloqueados
    completed_pct: float = 0.0
    unlocked: int = 0
    total: int = 0
    by_platform: dict[str, int] = field(default_factory=dict)   # desbloqueados por emulador
    by_grade: dict[str, int] = field(default_factory=dict)      # desbloqueados por grau
    rare_unlocked: int = 0              # ouro + platina desbloqueados
    rare_total: int = 0


def achievement_stats(games: list[GameAchievements]) -> AchievementStats:
    s = AchievementStats()
    by_platform: dict[str, int] = {}
    by_grade: dict[str, int] = {}
    for g in games:
        s.total_games += 1
        if g.total and g.unlocked_count == g.total:
            s.completed_games += 1
        for a in g.achievements:
            s.total += 1
            grade = a.grade.label
            is_rare = a.grade in (Grade.GOLD, Grade.PLATINUM)
            if is_rare:
                s.rare_total += 1
            if a.unlocked:
                s.unlocked += 1
                by_platform[g.emulator] = by_platform.get(g.emulator, 0) + 1
                by_grade[grade] = by_grade.get(grade, 0) + 1
                if is_rare:
                    s.rare_unlocked += 1
    s.by_platform = by_platform
    s.by_grade = by_grade
    s.completed_pct = (100.0 * s.completed_games / s.total_games
                       if s.total_games else 0.0)
    return s
