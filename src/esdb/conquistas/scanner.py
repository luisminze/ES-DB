"""Orquestra a leitura de conquistas dos três emuladores suportados.

Resolve pastas padrão e isola falhas por item (CONQUISTAS.md §6): uma leitura que
falha não derruba a varredura dos demais.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from .models import Achievement, GameAchievements, Grade
from .rpcs3 import scan_rpcs3
from .xenia import scan_xenia


def default_rpcs3_dirs() -> list[Path]:
    """Perfis de troféu do RPCS3: ``…/dev_hdd0/home/<perfil>/trophy``."""
    root = Path.home() / ".config/rpcs3/dev_hdd0/home"
    if not root.is_dir():
        return []
    return [p / "trophy" for p in sorted(root.iterdir())
            if (p / "trophy").is_dir()]


def default_shadps4_dir() -> Path | None:
    for cand in (Path.home() / ".local/share/shadPS4/trophy",
                 Path.home() / "shadPS4/user/trophy"):
        if cand.is_dir():
            return cand
    return None


def default_xenia_dir() -> Path | None:
    for cand in (Path.home() / ".local/share/Xenia/content",
                 Path.home() / ".local/share/xenia/content",
                 Path.home() / "Xenia/content",
                 Path.home() / ".xenia-canary/content"):
        if cand.is_dir():
            return cand
    return None


def _scan_shadps4(root: Path | None) -> list[GameAchievements]:
    """shadPS4: definições PS4 em XML (``*.SFM``); progresso ainda não lido."""
    if not root or not root.is_dir():
        return []
    games: list[GameAchievements] = []
    for sfm in sorted(root.glob("**/*.SFM"))[:200]:
        try:
            root_el = ET.parse(sfm).getroot()
        except (ET.ParseError, OSError):
            continue
        title = (root_el.findtext("title-name") or sfm.parent.name).strip()
        defs = []
        for t in root_el.findall("trophy"):
            grade = {"P": Grade.PLATINUM, "G": Grade.GOLD, "S": Grade.SILVER,
                     "B": Grade.BRONZE}.get((t.get("ttype") or "").upper(),
                                            Grade.UNKNOWN)
            defs.append(Achievement(
                key=(t.get("id") or "").strip(),
                name=(t.findtext("name") or "").strip(),
                description=(t.findtext("detail") or "").strip(),
                grade=grade,
                hidden=(t.get("hidden") or "no").lower() == "yes",
            ))
        if defs:
            games.append(GameAchievements("shadPS4", title, sfm.parent.name,
                                          str(sfm), defs, progress_available=False))
    return games


class ConquistasService:
    """Fachada usada pela interface para listar jogos com troféus."""

    def __init__(self, rpcs3_dir: str = "", shadps4_dir: str = "",
                 xenia_dir: str = "") -> None:
        self._rpcs3 = rpcs3_dir
        self._shadps4 = shadps4_dir
        self._xenia = xenia_dir

    def scan(self) -> list[GameAchievements]:
        games: list[GameAchievements] = []
        try:
            dirs = ([Path(self._rpcs3)] if self._rpcs3 else default_rpcs3_dirs())
            games += scan_rpcs3(dirs)
        except OSError:
            pass
        try:
            root = Path(self._shadps4) if self._shadps4 else default_shadps4_dir()
            games += _scan_shadps4(root)
        except OSError:
            pass
        try:
            root = Path(self._xenia) if self._xenia else default_xenia_dir()
            games += scan_xenia(root)
        except OSError:
            pass
        games.sort(key=lambda g: (g.emulator, g.title.lower()))
        return games

    def configured(self) -> bool:
        return bool(self._rpcs3 or default_rpcs3_dirs() or self._shadps4
                    or default_shadps4_dir())
