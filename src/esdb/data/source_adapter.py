"""Adaptador da fonte GameSessionTracker (SQLite somente leitura).

A conexão usa URI ``mode=ro`` e ``busy_timeout``; nunca escreve na fonte
(MAIN.md RNF-05, RNF-10). Detecta o protocolo aprimorado por ``PRAGMA
table_info`` (RASTREAMENTO_SESSOES.md §7), preferindo *snapshots* quando houver.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class SourceGame:
    id: int
    name: str
    platform: str
    system: str
    rom: str


@dataclass(slots=True)
class SourceSession:
    id: int
    game_id: int
    start_time: str
    end_time: str
    duration: int


@dataclass(slots=True)
class ProbeResult:
    ok: bool
    games: int
    sessions: int
    message: str = ""


_REQUIRED_TABLES = {"games", "sessions"}


def _connect_ro(path: Path) -> sqlite3.Connection:
    uri = f"file:{path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 4000")
    return conn


class GameSessionTrackerSqliteAdapter:
    """Lê ``games`` e ``sessions`` de um banco no esquema confirmado."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()

    def validate(self) -> ProbeResult:
        if not self.path.is_file():
            return ProbeResult(False, 0, 0, "Arquivo não encontrado.")
        try:
            conn = _connect_ro(self.path)
        except sqlite3.Error as exc:
            return ProbeResult(False, 0, 0, f"Falha ao abrir: {exc}")
        try:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            if not _REQUIRED_TABLES <= tables:
                missing = ", ".join(sorted(_REQUIRED_TABLES - tables))
                return ProbeResult(False, 0, 0, f"Tabelas ausentes: {missing}")
            games = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
            sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            return ProbeResult(True, games, sessions,
                               f"{games} jogos · {sessions} sessões")
        except sqlite3.Error as exc:
            return ProbeResult(False, 0, 0, str(exc))
        finally:
            conn.close()

    def list_games(self) -> list[SourceGame]:
        conn = _connect_ro(self.path)
        try:
            rows = conn.execute(
                "SELECT id, name, platform, COALESCE(system,'') AS system, "
                "COALESCE(rom,'') AS rom FROM games").fetchall()
            return [SourceGame(r["id"], r["name"], r["platform"], r["system"],
                               r["rom"]) for r in rows]
        finally:
            conn.close()

    def list_sessions_after(self, last_id: int = 0) -> list[SourceSession]:
        conn = _connect_ro(self.path)
        try:
            rows = conn.execute(
                "SELECT id, game_id, start_time, end_time, duration "
                "FROM sessions WHERE id > ? ORDER BY id", (last_id,)).fetchall()
            return [SourceSession(r["id"], r["game_id"], r["start_time"],
                                  r["end_time"], r["duration"]) for r in rows]
        finally:
            conn.close()
