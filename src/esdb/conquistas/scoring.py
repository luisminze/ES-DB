"""Pontuação e níveis locais de conquistas (ES-DB-Update1).

- **Sony (RPCS3, shadPS4)**: pontos por troféu desbloqueado, baseados no sistema
  oficial da Sony — Bronze=15, Prata=30, Ouro=90, Platina=300. O nível (categoria)
  vem do total acumulado: <300 Bronze, <600 Prata, <999 Ouro, >=999 Platina.
- **Xbox (Xenia)**: Gamerscore = soma do valor das conquistas desbloqueadas.

Tudo é calculado localmente a partir das conquistas já lidas (sem rede).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import GameAchievements, Grade

SONY_EMULATORS = ("RPCS3", "shadPS4")
SONY_POINTS = {
    Grade.BRONZE: 15,
    Grade.SILVER: 30,
    Grade.GOLD: 90,
    Grade.PLATINUM: 300,
}
# Limiares de categoria por pontos acumulados (ES-DB-Update1).
_LEVELS = [(999, "Platina"), (600, "Ouro"), (300, "Prata"), (0, "Bronze")]


@dataclass(slots=True)
class SonyScore:
    points: int = 0
    category: str = "Bronze"
    by_grade: dict[Grade, int] = field(default_factory=dict)   # troféus desbloqueados
    next_threshold: int | None = None                          # pontos p/ próximo nível
    progress: float = 0.0                                      # 0..1 dentro do nível


def _category(points: int) -> tuple[str, int | None, float]:
    for threshold, name in _LEVELS:
        if points >= threshold:
            idx = _LEVELS.index((threshold, name))
            lower = threshold
            upper = _LEVELS[idx - 1][0] if idx > 0 else None
            if upper is None:
                return name, None, 1.0
            span = upper - lower
            prog = (points - lower) / span if span else 1.0
            return name, upper, max(0.0, min(1.0, prog))
    return "Bronze", 300, 0.0


def sony_score(games: list[GameAchievements]) -> SonyScore:
    by_grade: dict[Grade, int] = {g: 0 for g in SONY_POINTS}
    points = 0
    for g in games:
        if g.emulator not in SONY_EMULATORS:
            continue
        for a in g.achievements:
            if a.unlocked and a.grade in SONY_POINTS:
                by_grade[a.grade] += 1
                points += SONY_POINTS[a.grade]
    category, nxt, prog = _category(points)
    return SonyScore(points, category, by_grade, nxt, prog)


def xbox_gamerscore(games: list[GameAchievements]) -> int:
    total = 0
    for g in games:
        if g.emulator != "Xenia":
            continue
        for a in g.achievements:
            if a.unlocked and a.gamerscore:
                total += a.gamerscore
    return total


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
