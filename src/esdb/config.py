"""Configuração do ES-DB e caminhos da pasta do programa (ESDE.md §2).

Tudo vive sob ``~/ES-DB`` (sobreponível por ``ES_DB_HOME``):
preferências em ``config.json``, banco derivado em ``derived/`` e cache em
``cache/``. A configuração é derivada em **passo único** do diretório do ES-DE.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import timezone
from pathlib import Path

from .data.source_adapter import GameSessionTrackerSqliteAdapter
from .domain.timeparse import local_offset
from .esde.resolver import DEFAULT_ESDE_HOME, discover_session_databases


def stats_home() -> Path:
    env = os.environ.get("ES_DB_HOME")
    return Path(env).expanduser() if env else Path.home() / "ES-DB"


def ensure_dirs() -> None:
    base = stats_home()
    for sub in ("database", "derived", "cache/thumbnails"):
        (base / sub).mkdir(parents=True, exist_ok=True)


def config_path() -> Path:
    return stats_home() / "config.json"


@dataclass(slots=True)
class AppConfig:
    esde_home: str = ""
    session_db: str = ""
    theme: str = "dark"                 # system | light | dark
    tz_offset_minutes: int | None = None
    auto_refresh_minutes: int = 0       # 0 = desligado
    rpcs3_dir: str = ""                 # pasta de troféus do RPCS3 (CONQUISTAS.md)
    shadps4_dir: str = ""
    xenia_dir: str = ""
    achievements_enabled: bool = True   # liga/desliga toda a área de Conquistas

    def tzinfo(self) -> timezone:
        if self.tz_offset_minutes is None:
            return local_offset()
        from datetime import timedelta
        return timezone(timedelta(minutes=self.tz_offset_minutes))

    def is_configured(self) -> bool:
        return bool(self.session_db) and Path(self.session_db).expanduser().is_file()


def autodetect() -> AppConfig:
    """Deriva uma configuração inicial do ambiente (RF-01)."""
    cfg = AppConfig()
    if DEFAULT_ESDE_HOME.is_dir():
        cfg.esde_home = str(DEFAULT_ESDE_HOME)
    best_path, best_sessions = "", -1
    for candidate in discover_session_databases():
        probe = GameSessionTrackerSqliteAdapter(candidate).validate()
        if probe.ok and probe.sessions > best_sessions:
            best_path, best_sessions = str(candidate), probe.sessions
    cfg.session_db = best_path

    from .conquistas.scanner import (default_rpcs3_dirs, default_shadps4_dir,
                                     default_xenia_dir)
    rpcs3 = default_rpcs3_dirs()
    cfg.rpcs3_dir = str(rpcs3[0]) if rpcs3 else ""
    shad = default_shadps4_dir()
    cfg.shadps4_dir = str(shad) if shad else ""
    xenia = default_xenia_dir()
    cfg.xenia_dir = str(xenia) if xenia else ""
    return cfg


def load_config() -> AppConfig:
    ensure_dirs()
    path = config_path()
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            known = {f for f in AppConfig.__slots__}  # type: ignore[attr-defined]
            return AppConfig(**{k: v for k, v in data.items() if k in known})
        except (json.JSONDecodeError, OSError, TypeError):
            pass
    cfg = autodetect()
    save_config(cfg)
    return cfg


def save_config(cfg: AppConfig) -> None:
    ensure_dirs()
    config_path().write_text(json.dumps(asdict(cfg), indent=2, ensure_ascii=False),
                             encoding="utf-8")
