"""Leitura dos ``gamelist.xml`` do ES-DE (ESDE.md §4, §6).

Somente leitura e tolerante a arquivos ausentes ou malformados (MAIN.md RNF-12).
O cache é por sistema: ``basename da ROM`` -> ``GameMetadata``.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from ..domain.models import GameMetadata


def _basename_of(path_text: str) -> str:
    name = os.path.basename((path_text or "").strip().lstrip("./").rstrip("/"))
    stem, _ = os.path.splitext(name)
    return stem


def _parse_release(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y%m%dT%H%M%S")
    except ValueError:
        try:
            return datetime.strptime(value.strip()[:8], "%Y%m%d")
        except ValueError:
            return None


def _parse_rating(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, min(1.0, float(value)))
    except ValueError:
        return None


def parse_gamelist(path: Path) -> dict[str, GameMetadata]:
    """Lê um ``gamelist.xml`` e indexa por basename da ROM."""
    out: dict[str, GameMetadata] = {}
    if not path.is_file():
        return out
    try:
        tree = ET.parse(path)
    except (ET.ParseError, OSError):
        return out
    root = tree.getroot()
    for game in root.findall("game"):
        base = _basename_of(game.findtext("path", ""))
        if not base:
            continue
        out[base] = GameMetadata(
            description=(game.findtext("desc") or "").strip(),
            genre=(game.findtext("genre") or "").strip(),
            developer=(game.findtext("developer") or "").strip(),
            publisher=(game.findtext("publisher") or "").strip(),
            rating=_parse_rating(game.findtext("rating")),
            release_date=_parse_release(game.findtext("releasedate")),
            players=(game.findtext("players") or "").strip(),
            source_path=str(path),
        )
    return out


class GamelistIndex:
    """Carrega e cacheia gamelists por sistema, sob demanda."""

    def __init__(self, resolver) -> None:
        self._resolver = resolver
        self._cache: dict[str, dict[str, GameMetadata]] = {}

    def metadata_for(self, system: str, rom_basename: str) -> GameMetadata | None:
        if not system or not rom_basename:
            return None
        if system not in self._cache:
            self._cache[system] = parse_gamelist(self._resolver.gamelist(system))
        return self._cache[system].get(rom_basename)
