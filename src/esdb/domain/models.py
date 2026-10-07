"""Modelos de domínio do ES-DB.

Os tempos são sempre ``datetime`` cientes de fuso (aware), preservando o offset
gravado na fonte (MAIN.md RNF-09). As durações são inteiros em segundos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DurationKind(str, Enum):
    """Classificação de qualidade de uma sessão (MAIN.md §7, §8)."""

    NORMAL = "normal"
    QUICK_LAUNCH = "quick_launch"          # duração zero
    INVALID_TIMESTAMP = "invalid_timestamp"
    NEGATIVE_DURATION = "negative_duration"
    DURATION_MISMATCH = "duration_mismatch"

    @property
    def is_valid(self) -> bool:
        """Sessões que entram em métricas de tempo (exclui zero e inválidas)."""
        return self is DurationKind.NORMAL

    @property
    def counts_as_session(self) -> bool:
        """Normais e inícios rápidos contam no total de sessões."""
        return self in (DurationKind.NORMAL, DurationKind.QUICK_LAUNCH)


@dataclass(slots=True)
class GameMetadata:
    """Metadados ricos vindos do ``gamelist.xml`` do ES-DE (ESDE.md §6)."""

    description: str = ""
    genre: str = ""
    developer: str = ""
    publisher: str = ""
    rating: float | None = None            # 0.0–1.0
    release_date: datetime | None = None
    players: str = ""
    source_path: str = ""


@dataclass(slots=True)
class Game:
    """Jogo conhecido, identidade estável por ``external_id`` (games.id)."""

    external_id: int
    name: str
    platform: str
    system: str = ""
    rom_raw: str = ""
    rom_basename: str = ""
    cover_path: str | None = None
    metadata: GameMetadata | None = None
    # Agregados preenchidos pela biblioteca (todo o histórico):
    total_seconds: int = 0
    session_count: int = 0
    first_played_at: datetime | None = None
    last_played_at: datetime | None = None

    @property
    def display_title(self) -> str:
        """Prefere o nome limpo do gamelist, se houver; senão o nome da fonte."""
        if self.metadata and self.metadata.description and self.name:
            return self.name
        return self.name or self.rom_basename or f"Jogo #{self.external_id}"


@dataclass(slots=True)
class Session:
    """Sessão importada, já parseada e classificada."""

    external_id: int
    game_id: int
    started_at: datetime
    ended_at: datetime
    duration_seconds: int
    kind: DurationKind = DurationKind.NORMAL

    @property
    def is_valid(self) -> bool:
        return self.kind.is_valid


@dataclass(slots=True)
class ImportIssue:
    """Problema de integridade registrado na importação (MAIN.md RF-09)."""

    external_id: int
    type: str
    details: str


@dataclass(slots=True)
class ImportResult:
    """Resumo de uma sincronização (MAIN.md RF-02)."""

    imported: int = 0
    skipped: int = 0
    errors: int = 0
    games: int = 0
    issues: list[ImportIssue] = field(default_factory=list)
    synced_at: datetime | None = None
