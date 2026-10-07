"""Gravação opcional e local: criar banco e instalar scripts do ES-DE.

Escreve apenas em arquivos que pertencem ao ES-DB (o banco escolhido) e na pasta
``scripts/`` do ES-DE, onde só mexe nos próprios scripts (marcador de origem).
Nunca toca nas demais fontes analisadas (ESDE.md §5, §7; RNF-05).
"""

from __future__ import annotations

import os
import sqlite3
import stat
from pathlib import Path

MARKER = "# gerado-por: ES-DB"

# Mapa sistema → nome legível (espelha o script de referência do ES-DE).
PLATFORM_MAP: dict[str, str] = {
    "nes": "Nintendo NES", "famicom": "Nintendo Famicom",
    "snes": "Nintendo SNES (Super Nintendo)", "n64": "Nintendo 64",
    "gc": "Nintendo GameCube", "wii": "Nintendo Wii", "wiiu": "Nintendo Wii U",
    "switch": "Nintendo Switch", "gb": "Nintendo Game Boy",
    "gbc": "Nintendo Game Boy Color", "gba": "Nintendo Game Boy Advance",
    "nds": "Nintendo DS", "3ds": "Nintendo 3DS", "virtualboy": "Nintendo Virtual Boy",
    "psx": "Sony PlayStation", "ps2": "Sony PlayStation 2",
    "ps3": "Sony PlayStation 3", "psp": "Sony PlayStation Portable",
    "psvita": "Sony PlayStation Vita", "xbox": "Microsoft Xbox",
    "xbox360": "Microsoft Xbox 360", "genesis": "Sega Mega Drive (Genesis)",
    "megadrive": "Sega Mega Drive (Genesis)", "mastersystem": "Sega Master System",
    "gamegear": "Sega Game Gear", "saturn": "Sega Saturn",
    "dreamcast": "Sega Dreamcast", "segacd": "Sega CD", "sega32x": "Sega 32X",
    "pcengine": "NEC PC Engine (TurboGrafx-16)", "neogeo": "SNK Neo Geo",
    "arcade": "Arcade", "mame": "Arcade (MAME)", "atari2600": "Atari 2600",
    "atari7800": "Atari 7800", "atarilynx": "Atari Lynx",
    "atarijaguar": "Atari Jaguar", "c64": "Commodore 64", "amiga": "Commodore Amiga",
    "dos": "MS-DOS", "scummvm": "ScummVM", "ports": "Ports",
}

_SCHEMA_SQL = """CREATE TABLE IF NOT EXISTS games (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, platform TEXT NOT NULL,
  system TEXT, rom TEXT, UNIQUE(name, platform));
CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, game_id INTEGER NOT NULL,
  start_time TEXT NOT NULL, end_time TEXT NOT NULL, duration INTEGER NOT NULL,
  FOREIGN KEY(game_id) REFERENCES games(id));
CREATE INDEX IF NOT EXISTS idx_sessions_game ON sessions(game_id);
CREATE INDEX IF NOT EXISTS idx_sessions_start ON sessions(start_time);"""


def create_database(path: str | Path, overwrite: bool = False) -> Path:
    """Cria um SQLite vazio no esquema GameSessionTracker. Nunca sobrescreve sem
    ``overwrite=True`` (ESDE.md §5)."""
    target = Path(path).expanduser()
    if target.exists() and not overwrite:
        raise FileExistsError(f"O arquivo já existe: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target))
    try:
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()
    return target


def _runtime_dir(db_path: Path) -> Path:
    return db_path.parent / ".gametracker"


def _start_script(db_path: Path) -> str:
    runtime = _runtime_dir(db_path) / "current_session"
    return f"""#!/usr/bin/env bash
{MARKER}
# Evento game-start do ES-DE. Argumentos: $1=ROM $2=arquivo $3=nome $4=sistema.
set -euo pipefail
RUNTIME="{runtime}"
mkdir -p "$(dirname "$RUNTIME")"
ROM="${{1:-}}"
NAME="${{3:-}}"
SYSTEM="${{4:-}}"
printf '%s\\n%s\\n%s\\n%s\\n' \\
  "$(date +%Y-%m-%dT%H:%M:%S%z)" "$NAME" "$SYSTEM" "$ROM" > "$RUNTIME"
exit 0
"""


def _platform_case() -> str:
    lines = ["  case \"$SYSTEM\" in"]
    for sysk, name in PLATFORM_MAP.items():
        lines.append(f"    {sysk}) PLATFORM='{name}' ;;")
    lines.append("    *) PLATFORM=\"$SYSTEM\" ;;")
    lines.append("  esac")
    return "\n".join(lines)


def _end_script(db_path: Path) -> str:
    runtime = _runtime_dir(db_path) / "current_session"
    return f"""#!/usr/bin/env bash
{MARKER}
# Evento game-end do ES-DE. Lê o início gravado e insere a sessão no banco.
set -euo pipefail
DB="{db_path}"
RUNTIME="{runtime}"
[ -f "$RUNTIME" ] || exit 0

END="$(date +%Y-%m-%dT%H:%M:%S%z)"
START="$(sed -n '1p' "$RUNTIME")"
NAME="$(sed -n '2p' "$RUNTIME")"
SYSTEM="$(sed -n '3p' "$RUNTIME")"
ROM="$(sed -n '4p' "$RUNTIME")"
rm -f "$RUNTIME"
[ -n "$START" ] && [ -n "$NAME" ] || exit 0

S="$(date -d "$START" +%s 2>/dev/null || echo 0)"
E="$(date -d "$END" +%s 2>/dev/null || echo 0)"
DUR=$(( E - S ))
[ "$DUR" -lt 0 ] && DUR=0

{_platform_case()}

esc() {{ printf "%s" "$1" | sed "s/'/''/g"; }}
NAME_E="$(esc "$NAME")"
PLATFORM_E="$(esc "$PLATFORM")"
SYSTEM_E="$(esc "$SYSTEM")"
ROM_E="$(esc "$ROM")"

mkdir -p "$(dirname "$DB")"
sqlite3 "$DB" <<SQL
{_SCHEMA_SQL}
INSERT INTO games(name, platform, system, rom) VALUES('$NAME_E','$PLATFORM_E','$SYSTEM_E','$ROM_E')
  ON CONFLICT(name, platform) DO UPDATE SET system=excluded.system, rom=excluded.rom;
INSERT INTO sessions(game_id, start_time, end_time, duration)
  SELECT id, '$START', '$END', $DUR FROM games WHERE name='$NAME_E' AND platform='$PLATFORM_E';
SQL
exit 0
"""


def install_scripts(scripts_dir: str | Path, db_path: str | Path) -> list[Path]:
    """Instala ``game-start``/``game-end`` apontando para ``db_path``."""
    scripts = Path(scripts_dir).expanduser()
    db = Path(db_path).expanduser()
    written: list[Path] = []
    for event, body in (("game-start", _start_script(db)),
                        ("game-end", _end_script(db))):
        folder = scripts / event
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / "esdb-tracker.sh"
        target.write_text(body, encoding="utf-8")
        target.chmod(target.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        written.append(target)
    return written


def remove_scripts(scripts_dir: str | Path) -> list[Path]:
    """Remove apenas scripts gerados pelo ES-DB (preserva os demais)."""
    scripts = Path(scripts_dir).expanduser()
    removed: list[Path] = []
    for event in ("game-start", "game-end"):
        folder = scripts / event
        if not folder.is_dir():
            continue
        for f in folder.glob("*.sh"):
            try:
                if MARKER in f.read_text(encoding="utf-8", errors="ignore"):
                    f.unlink()
                    removed.append(f)
            except OSError:
                continue
    return removed


def scripts_installed(scripts_dir: str | Path) -> bool:
    scripts = Path(scripts_dir).expanduser()
    for event in ("game-start", "game-end"):
        folder = scripts / event
        if folder.is_dir():
            for f in folder.glob("*.sh"):
                try:
                    if MARKER in f.read_text(encoding="utf-8", errors="ignore"):
                        return True
                except OSError:
                    continue
    return False
