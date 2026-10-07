"""Descoberta automática de recursos a partir do diretório do ES-DE (ESDE.md §3)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_ESDE_HOME = Path.home() / "ES-DE"

MEDIA_KINDS = (
    "covers", "screenshots", "marquees", "miximages", "3dboxes", "backcovers",
    "fanart", "physicalmedia", "titlescreens", "videos", "manuals",
)


@dataclass(slots=True)
class EsdeLayout:
    """Caminhos resolvidos dentro do diretório do ES-DE."""

    home: Path
    scripts: Path
    downloaded_media: Path
    gamelists: Path
    settings: Path

    def exists(self) -> bool:
        return self.home.is_dir()

    def media_dir(self, system: str, kind: str = "covers") -> Path:
        return self.downloaded_media / system / kind

    def gamelist(self, system: str) -> Path:
        return self.gamelists / system / "gamelist.xml"

    def found(self) -> dict[str, bool]:
        """Mapa do que foi encontrado, para a tela de configuração."""
        return {
            "scripts": self.scripts.is_dir(),
            "downloaded_media": self.downloaded_media.is_dir(),
            "gamelists": self.gamelists.is_dir(),
            "settings": (self.settings / "es_settings.xml").is_file(),
        }


def resolve_esde(home: str | Path | None = None) -> EsdeLayout:
    base = Path(home).expanduser() if home else DEFAULT_ESDE_HOME
    return EsdeLayout(
        home=base,
        scripts=base / "scripts",
        downloaded_media=base / "downloaded_media",
        gamelists=base / "gamelists",
        settings=base / "settings",
    )


def discover_session_databases() -> list[Path]:
    """Bancos de sessão candidatos, mais provável primeiro (ESDE.md §3)."""
    out: list[Path] = []
    stats_db = Path.home() / "ES-DE-STATS" / "DATABASE"
    if stats_db.is_dir():
        out.extend(sorted(p for p in stats_db.glob("*.db")))
    legacy = Path.home() / "GameSessionTracker" / "database" / "games.db"
    if legacy.is_file():
        out.append(legacy)
    return out
