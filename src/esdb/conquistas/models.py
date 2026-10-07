"""Modelos de conquistas (CONQUISTAS.md §4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Grade(str, Enum):
    PLATINUM = "platinum"
    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"
    GAMERSCORE = "gamerscore"
    UNKNOWN = "unknown"

    @property
    def label(self) -> str:
        return {
            Grade.PLATINUM: "Platina", Grade.GOLD: "Ouro",
            Grade.SILVER: "Prata", Grade.BRONZE: "Bronze",
            Grade.GAMERSCORE: "Gamerscore", Grade.UNKNOWN: "—",
        }[self]


@dataclass(slots=True)
class Achievement:
    key: str                      # id dentro do set (ex.: "031")
    name: str
    description: str
    grade: Grade = Grade.UNKNOWN
    hidden: bool = False
    unlocked: bool = False
    unlocked_at: datetime | None = None
    icon_path: str | None = None
    gamerscore: int | None = None

    def display_name(self) -> str:
        if self.hidden and not self.unlocked:
            return "Troféu oculto"
        return self.name

    def display_description(self) -> str:
        if self.hidden and not self.unlocked:
            return "Detalhes ocultos até o desbloqueio."
        return self.description


@dataclass(slots=True)
class GameAchievements:
    emulator: str                 # RPCS3 | Xenia | shadPS4
    title: str
    comm_id: str                  # NPWR..., título técnico
    source_path: str
    achievements: list[Achievement] = field(default_factory=list)
    progress_available: bool = True
    icon_path: str | None = None

    @property
    def unlocked_count(self) -> int:
        return sum(1 for a in self.achievements if a.unlocked)

    @property
    def total(self) -> int:
        return len(self.achievements)

    @property
    def percent(self) -> float:
        return (100.0 * self.unlocked_count / self.total) if self.total else 0.0
