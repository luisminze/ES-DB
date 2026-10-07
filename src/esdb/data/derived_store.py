"""Banco derivado local (``~/ES-DE-STATS/derived/derived.db``).

Persiste sessões/jogos importados (para sincronização **incremental** e
idempotente por ``sessions.id``), o catálogo de bancos geridos, as predefinições
de filtros, as correções locais (overrides) e o cursor de sincronização.

É o único SQLite em que o ES-DB **escreve**; as fontes analisadas continuam em
somente leitura (MAIN.md §7, RNF-05).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from ..domain.models import DurationKind, Session
from .source_adapter import SourceGame

_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_settings(
  key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS managed_source(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
  path TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sync_state(
  source_path TEXT PRIMARY KEY, last_session_id INTEGER NOT NULL DEFAULT 0,
  last_sync_at TEXT);
CREATE TABLE IF NOT EXISTS d_game(
  source_path TEXT NOT NULL, external_id INTEGER NOT NULL,
  name TEXT, platform TEXT, system TEXT, rom TEXT,
  PRIMARY KEY(source_path, external_id));
CREATE TABLE IF NOT EXISTS d_session(
  source_path TEXT NOT NULL, external_id INTEGER NOT NULL, game_id INTEGER,
  started_at TEXT, ended_at TEXT, duration INTEGER, kind TEXT,
  PRIMARY KEY(source_path, external_id));
CREATE INDEX IF NOT EXISTS idx_dsession_src ON d_session(source_path);
CREATE TABLE IF NOT EXISTS game_override(
  source_path TEXT NOT NULL, external_id INTEGER NOT NULL,
  title_override TEXT, cover_override_path TEXT,
  PRIMARY KEY(source_path, external_id));
"""


class DerivedStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------ settings
    def get_setting(self, key: str, default=None):
        row = self._conn.execute(
            "SELECT value FROM user_settings WHERE key=?", (key,)).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row["value"])
        except json.JSONDecodeError:
            return default

    def set_setting(self, key: str, value) -> None:
        self._conn.execute(
            "INSERT INTO user_settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json.dumps(value, ensure_ascii=False)))
        self._conn.commit()

    # --------------------------------------------------------- presets (FILTROS)
    def get_presets(self) -> dict[str, dict]:
        return self.get_setting("filter_presets", {}) or {}

    def save_preset(self, name: str, data: dict) -> None:
        presets = self.get_presets()
        presets[name] = data
        self.set_setting("filter_presets", presets)

    def delete_preset(self, name: str) -> None:
        presets = self.get_presets()
        presets.pop(name, None)
        self.set_setting("filter_presets", presets)

    # ------------------------------------------------------ managed sources
    def list_managed(self) -> list[dict]:
        return [dict(r) for r in self._conn.execute(
            "SELECT id, name, path, created_at FROM managed_source "
            "ORDER BY created_at")]

    def add_managed(self, name: str, path: str) -> None:
        self._conn.execute(
            "INSERT INTO managed_source(name, path, created_at) VALUES(?,?,?) "
            "ON CONFLICT(path) DO UPDATE SET name=excluded.name",
            (name, path, datetime.now().isoformat(timespec="seconds")))
        self._conn.commit()

    def remove_managed(self, path: str) -> None:
        self._conn.execute("DELETE FROM managed_source WHERE path=?", (path,))
        self._conn.commit()

    # -------------------------------------------------------------- sync
    def get_cursor(self, source_path: str) -> int:
        row = self._conn.execute(
            "SELECT last_session_id FROM sync_state WHERE source_path=?",
            (source_path,)).fetchone()
        return row["last_session_id"] if row else 0

    def set_cursor(self, source_path: str, last_id: int) -> None:
        self._conn.execute(
            "INSERT INTO sync_state(source_path, last_session_id, last_sync_at) "
            "VALUES(?,?,?) ON CONFLICT(source_path) DO UPDATE SET "
            "last_session_id=excluded.last_session_id, last_sync_at=excluded.last_sync_at",
            (source_path, last_id, datetime.now().isoformat(timespec="seconds")))
        self._conn.commit()

    def reset_source(self, source_path: str) -> None:
        for table in ("d_game", "d_session", "sync_state"):
            col = "source_path"
            self._conn.execute(f"DELETE FROM {table} WHERE {col}=?", (source_path,))
        self._conn.commit()

    # ---------------------------------------------------------- upserts
    def upsert_games(self, source_path: str, games: list[SourceGame]) -> None:
        self._conn.executemany(
            "INSERT INTO d_game(source_path, external_id, name, platform, system, rom) "
            "VALUES(?,?,?,?,?,?) ON CONFLICT(source_path, external_id) DO UPDATE SET "
            "name=excluded.name, platform=excluded.platform, system=excluded.system, "
            "rom=excluded.rom",
            [(source_path, g.id, g.name, g.platform, g.system, g.rom) for g in games])
        self._conn.commit()

    def upsert_sessions(self, source_path: str, sessions: list[Session]) -> None:
        self._conn.executemany(
            "INSERT INTO d_session(source_path, external_id, game_id, started_at, "
            "ended_at, duration, kind) VALUES(?,?,?,?,?,?,?) "
            "ON CONFLICT(source_path, external_id) DO NOTHING",
            [(source_path, s.external_id, s.game_id, s.started_at.isoformat(),
              s.ended_at.isoformat(), s.duration_seconds, s.kind.value)
             for s in sessions])
        self._conn.commit()

    # ----------------------------------------------------------- loads
    def load_games(self, source_path: str) -> list[SourceGame]:
        rows = self._conn.execute(
            "SELECT external_id, name, platform, system, rom FROM d_game "
            "WHERE source_path=?", (source_path,))
        return [SourceGame(r["external_id"], r["name"], r["platform"],
                           r["system"] or "", r["rom"] or "") for r in rows]

    def load_sessions(self, source_path: str) -> list[Session]:
        rows = self._conn.execute(
            "SELECT external_id, game_id, started_at, ended_at, duration, kind "
            "FROM d_session WHERE source_path=?", (source_path,))
        out: list[Session] = []
        for r in rows:
            try:
                started = datetime.fromisoformat(r["started_at"])
                ended = datetime.fromisoformat(r["ended_at"])
            except (ValueError, TypeError):
                continue
            try:
                kind = DurationKind(r["kind"])
            except ValueError:
                kind = DurationKind.NORMAL
            out.append(Session(r["external_id"], r["game_id"], started, ended,
                               r["duration"], kind))
        return out

    # -------------------------------------------------------- overrides
    def get_overrides(self, source_path: str) -> dict[int, dict]:
        rows = self._conn.execute(
            "SELECT external_id, title_override, cover_override_path "
            "FROM game_override WHERE source_path=?", (source_path,))
        return {r["external_id"]: {"title": r["title_override"],
                                   "cover": r["cover_override_path"]} for r in rows}

    def set_override(self, source_path: str, external_id: int,
                     title: str | None = None, cover: str | None = None) -> None:
        self._conn.execute(
            "INSERT INTO game_override(source_path, external_id, title_override, "
            "cover_override_path) VALUES(?,?,?,?) "
            "ON CONFLICT(source_path, external_id) DO UPDATE SET "
            "title_override=excluded.title_override, "
            "cover_override_path=excluded.cover_override_path",
            (source_path, external_id, title, cover))
        self._conn.commit()
