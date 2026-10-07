"""Repositório em memória: carrega a fonte, classifica e enriquece com o ES-DE.

Para a escala alvo (até ~100k sessões) manter tudo em memória é suficiente e
simples; agregações usam a camada de domínio. Toda leitura é somente leitura.
"""

from __future__ import annotations

from datetime import datetime, tzinfo

from ..domain.calculations import Metrics, Period, compute_metrics
from ..domain.models import (DurationKind, Game, ImportIssue, ImportResult,
                             Session)
from ..esde.gamelist import GamelistIndex
from ..esde.media import MediaResolver
from ..esde.resolver import EsdeLayout, resolve_esde
from ..esde.rom import rom_basename
from .derived_store import DerivedStore
from .importer import classify_session
from .source_adapter import GameSessionTrackerSqliteAdapter


class Library:
    """Estado consolidado de uma fonte, pronto para a interface consumir.

    A importação é **incremental**: só sessões com ``id`` acima do cursor são
    lidas e persistidas no banco derivado; depois o estado é recarregado dele.
    """

    def __init__(self, session_db: str, esde_home: str, tz: tzinfo,
                 derived_db: str) -> None:
        self.session_db = session_db
        self.tz = tz
        self.layout: EsdeLayout = resolve_esde(esde_home or None)
        self._media = MediaResolver(self.layout)
        self._gamelist = GamelistIndex(self.layout)
        self.store = DerivedStore(derived_db)
        self.games: list[Game] = []
        self.games_by_id: dict[int, Game] = {}
        self.sessions: list[Session] = []
        self.platforms: list[str] = []
        self.result = ImportResult()

    # ------------------------------------------------------------------ load
    def load(self) -> ImportResult:
        adapter = GameSessionTrackerSqliteAdapter(self.session_db)
        probe = adapter.validate()
        result = ImportResult(synced_at=datetime.now(self.tz))
        if not probe.ok:
            result.errors = 1
            result.issues.append(ImportIssue(0, "source", probe.message))
            self.result = result
            return result

        src_path = self.session_db
        # Importação incremental por sessions.id (idempotente).
        cursor = self.store.get_cursor(src_path)
        new_src = adapter.list_sessions_after(cursor)
        classified = [classify_session(s, self.tz) for s in new_src]
        self.store.upsert_sessions(src_path, classified)
        self.store.upsert_games(src_path, adapter.list_games())
        if new_src:
            self.store.set_cursor(src_path, max(s.id for s in new_src))
        result.imported = len(new_src)

        # Recarrega o estado consolidado do banco derivado.
        src_games = {g.id: g for g in self.store.load_games(src_path)}
        self.sessions = self.store.load_sessions(src_path)
        self._collect_issues(src_games, result)
        self._build_games(src_games)
        result.games = len(self.games)
        self.result = result
        return result

    def _collect_issues(self, src_games: dict, result: ImportResult) -> None:
        for s in self.sessions:
            if s.game_id not in src_games:
                result.issues.append(ImportIssue(s.external_id, "orphan_session",
                                                 "Sessão sem jogo no JOIN"))
            if s.kind in (DurationKind.INVALID_TIMESTAMP,
                          DurationKind.NEGATIVE_DURATION,
                          DurationKind.DURATION_MISMATCH):
                result.issues.append(ImportIssue(s.external_id, s.kind.value,
                                                 "Sessão sinalizada para revisão"))

    def _build_games(self, src_games: dict[int, object]) -> None:
        overrides = self.store.get_overrides(self.session_db)
        agg: dict[int, dict] = {}
        for s in self.sessions:
            a = agg.setdefault(s.game_id, {"secs": 0, "count": 0,
                                           "first": None, "last": None})
            if s.kind.counts_as_session:
                a["count"] += 1
            if s.is_valid:
                a["secs"] += s.duration_seconds
                if a["first"] is None or s.started_at < a["first"]:
                    a["first"] = s.started_at
                if a["last"] is None or s.ended_at > a["last"]:
                    a["last"] = s.ended_at

        games: list[Game] = []
        for gid, src in src_games.items():
            base = rom_basename(src.rom)  # type: ignore[attr-defined]
            system = src.system  # type: ignore[attr-defined]
            cover = self._media.cover_for(system, base)
            meta = self._gamelist.metadata_for(system, base)
            a = agg.get(gid, {})
            ov = overrides.get(gid, {})
            cover_path = ov.get("cover") or (str(cover) if cover else None)
            games.append(Game(
                external_id=gid,
                name=ov.get("title") or src.name,  # type: ignore[attr-defined]
                platform=src.platform,  # type: ignore[attr-defined]
                system=system,
                rom_raw=src.rom,  # type: ignore[attr-defined]
                rom_basename=base,
                cover_path=cover_path,
                metadata=meta,
                total_seconds=a.get("secs", 0),
                session_count=a.get("count", 0),
                first_played_at=a.get("first"),
                last_played_at=a.get("last"),
            ))
        games.sort(key=lambda g: g.total_seconds, reverse=True)
        self.games = games
        self.games_by_id = {g.external_id: g for g in games}
        self.platforms = sorted({g.platform for g in games if g.platform})

    # --------------------------------------------------------------- queries
    def metrics(self, period: Period) -> Metrics:
        return compute_metrics(self.sessions, self.games_by_id, period, self.tz)

    def sessions_for_game(self, game_id: int) -> list[Session]:
        rows = [s for s in self.sessions if s.game_id == game_id]
        rows.sort(key=lambda s: s.started_at, reverse=True)
        return rows

    def screenshots_for(self, game: Game) -> list[str]:
        return [str(p) for p in self._media.screenshots_for(game.system,
                                                            game.rom_basename)]

    def genres(self) -> list[str]:
        return sorted({g.metadata.genre for g in self.games
                       if g.metadata and g.metadata.genre})

    def developers(self) -> list[str]:
        return sorted({g.metadata.developer for g in self.games
                       if g.metadata and g.metadata.developer})

    def has_metadata(self) -> bool:
        return any(g.metadata for g in self.games)
