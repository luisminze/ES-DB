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


def clear_game_data(db_path: str | Path, game_id: int) -> bool:
    """Apaga **permanentemente** as sessões e o registro de um jogo no banco de
    sessões do ES-DB. Retorna ``True`` se algo foi apagado."""
    target = Path(db_path).expanduser()
    if not target.is_file():
        return False
    conn = sqlite3.connect(str(target))
    try:
        changed = conn.execute(
            "DELETE FROM sessions WHERE game_id=?", (game_id,)).rowcount
        changed += conn.execute(
            "DELETE FROM games WHERE id=?", (game_id,)).rowcount
        conn.commit()
    except sqlite3.OperationalError:
        return False
    finally:
        conn.close()
    return changed > 0


def clear_all_data(db_path: str | Path) -> bool:
    """Apaga **permanentemente** todas as sessões e jogos do banco de sessões."""
    target = Path(db_path).expanduser()
    if not target.is_file():
        return False
    conn = sqlite3.connect(str(target))
    try:
        conn.execute("DELETE FROM sessions")
        conn.execute("DELETE FROM games")
        conn.commit()
    except sqlite3.OperationalError:
        return False
    finally:
        conn.close()
    return True


def sync_lutris_rows(db_path: str | Path, data_dir: str | Path | None = None) -> int:
    """Normaliza as linhas de jogos do Lutris no banco de sessões para a
    plataforma **exata** do ``pga.db`` (ex.: ``PC (Lutris)`` → ``Sony
    PlayStation``), evitando duplicatas quando o script passa a gravar a
    plataforma exata. Idempotente: não faz nada se já estiver correto ou se o
    ``pga.db`` não existir. Retorna quantas linhas foram ajustadas."""
    from .lutris import LutrisIndex

    target = Path(db_path).expanduser()
    if not target.is_file():
        return 0
    idx = LutrisIndex(data_dir)
    if not idx.available:
        return 0
    conn = sqlite3.connect(str(target))
    changed = 0
    try:
        rows = conn.execute(
            "SELECT id, name, platform, system FROM games "
            "WHERE system LIKE 'lutris%'").fetchall()
        for gid, name, platform, system in rows:
            exact = idx.platform_for(name)
            tag = idx.system_tag_for(name)
            if not exact or (platform == exact and system == tag):
                continue
            other = conn.execute(
                "SELECT id FROM games WHERE name=? AND platform=? AND id<>?",
                (name, exact, gid)).fetchone()
            if other:  # já existe a linha exata: funde as sessões e remove esta
                conn.execute("UPDATE sessions SET game_id=? WHERE game_id=?",
                             (other[0], gid))
                conn.execute("DELETE FROM games WHERE id=?", (gid,))
                conn.execute("UPDATE games SET system=? WHERE id=?",
                             (tag, other[0]))
            else:
                conn.execute("UPDATE games SET platform=?, system=? WHERE id=?",
                             (exact, tag, gid))
            changed += 1
        conn.commit()
    except sqlite3.OperationalError:
        return 0
    finally:
        conn.close()
    return changed


def _runtime_dir(db_path: Path) -> Path:
    return db_path.parent / ".gametracker"


def _export_dir(db_path: Path) -> Path:
    # ~/ES-DB/exports quando o banco está em ~/ES-DB/database/<nome>.db
    if db_path.parent.name == "database":
        return db_path.parent.parent / "exports"
    return db_path.parent / "exports"


_LOG_FN = (
    'log() { printf "[%s] %s\\n" "$(date \'+%Y-%m-%d %H:%M:%S\')" "$*" >> "$LOG"; }'
)


def _start_script(db_path: Path) -> str:
    rt = _runtime_dir(db_path)
    return f"""#!/usr/bin/env bash
{MARKER}
# Evento game-start do ES-DE. Argumentos do ES-DE:
#   $1=ROM  $2=nome do jogo  $3=sistema (curto)  $4=plataforma (nome completo).
set -euo pipefail
RUNTIME_DIR="{rt}"
RUNTIME="$RUNTIME_DIR/current_session"
LOG="$RUNTIME_DIR/tracker.log"
mkdir -p "$RUNTIME_DIR"
{_LOG_FN}
ROM="${{1:-}}"
NAME="${{2:-}}"
SYSTEM="${{3:-}}"
PLATFORM="${{4:-}}"
if [ -z "$NAME" ]; then log "ERRO: nome ausente no game-start"; exit 0; fi
printf '%s\\n%s\\n%s\\n%s\\n%s\\n' \\
  "$(date +%Y-%m-%dT%H:%M:%S%z)" "$NAME" "$SYSTEM" "$PLATFORM" "$ROM" > "$RUNTIME"
log "Sessão iniciada: $NAME [${{PLATFORM:-$SYSTEM}}]"
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
    rt = _runtime_dir(db_path)
    return f"""#!/usr/bin/env bash
{MARKER}
# Evento game-end do ES-DE. Lê o início gravado e insere a sessão no banco.
set -euo pipefail
DB="{db_path}"
RUNTIME_DIR="{rt}"
RUNTIME="$RUNTIME_DIR/current_session"
LOG="$RUNTIME_DIR/tracker.log"
EXPORT="$RUNTIME_DIR/export.sh"
{_LOG_FN}
[ -f "$RUNTIME" ] || exit 0

END="$(date +%Y-%m-%dT%H:%M:%S%z)"
START="$(sed -n '1p' "$RUNTIME")"
NAME="$(sed -n '2p' "$RUNTIME")"
SYSTEM="$(sed -n '3p' "$RUNTIME")"
PLATFORM="$(sed -n '4p' "$RUNTIME")"
ROM="$(sed -n '5p' "$RUNTIME")"
rm -f "$RUNTIME"
[ -n "$START" ] && [ -n "$NAME" ] || exit 0

S="$(date -d "$START" +%s 2>/dev/null || echo 0)"
E="$(date -d "$END" +%s 2>/dev/null || echo 0)"
DUR=$(( E - S ))
[ "$DUR" -lt 0 ] && DUR=0

# O ES-DE já fornece a plataforma em $4; se vier vazia, deriva do sistema.
if [ -z "$PLATFORM" ]; then
{_platform_case()}
fi

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
log "Sessão encerrada: $NAME [$PLATFORM] (${{DUR}}s)"
[ -x "$EXPORT" ] && "$EXPORT" >/dev/null 2>&1 || true
exit 0
"""


def _export_script(db_path: Path) -> str:
    """Adaptação do export.sh do GameSessionTracker para a pasta do ES-DB."""
    export_dir = _export_dir(db_path)
    rt = _runtime_dir(db_path)
    return f"""#!/usr/bin/env bash
{MARKER}
# Exporta sessões e resumo por jogo para CSV/TXT (adaptado do GameSessionTracker).
set -euo pipefail
DB="{db_path}"
EXPORT_DIR="{export_dir}"
LOG="{rt}/tracker.log"
mkdir -p "$EXPORT_DIR"
[ -f "$DB" ] || exit 0

sqlite3 -header -csv "$DB" "
SELECT sessions.id AS session_id, games.name AS game, games.platform AS platform,
       games.system AS system, games.rom AS rom, sessions.start_time AS start_time,
       sessions.end_time AS end_time, sessions.duration AS duration_seconds
FROM sessions JOIN games ON games.id = sessions.game_id
ORDER BY sessions.start_time;" > "$EXPORT_DIR/sessions.csv"

{{
  printf 'ID | Jogo | Plataforma | Sistema | Início | Fim | Duração | ROM\\n'
  printf '%s\\n' '----------------------------------------------------------------------'
  sqlite3 -separator ' | ' "$DB" "
  SELECT sessions.id, games.name, games.platform, games.system,
         sessions.start_time, sessions.end_time,
         printf('%02d:%02d:%02d', sessions.duration/3600,
                (sessions.duration%3600)/60, sessions.duration%60),
         games.rom
  FROM sessions JOIN games ON games.id = sessions.game_id
  ORDER BY sessions.start_time;"
}} > "$EXPORT_DIR/sessions.txt"

sqlite3 -header -csv "$DB" "
SELECT games.name AS game, games.platform AS platform,
       COUNT(sessions.id) AS sessions, SUM(sessions.duration) AS total_seconds,
       MIN(sessions.start_time) AS first_session, MAX(sessions.end_time) AS last_session
FROM sessions JOIN games ON games.id = sessions.game_id
GROUP BY games.id ORDER BY SUM(sessions.duration) DESC;" > "$EXPORT_DIR/games_summary.csv"

{{
  printf 'Jogo | Plataforma | Sessões | Tempo total | Primeira | Última\\n'
  printf '%s\\n' '----------------------------------------------------------------------'
  sqlite3 -separator ' | ' "$DB" "
  SELECT games.name, games.platform, COUNT(sessions.id),
         printf('%02d:%02d:%02d', SUM(sessions.duration)/3600,
                (SUM(sessions.duration)%3600)/60, SUM(sessions.duration)%60),
         MIN(sessions.start_time), MAX(sessions.end_time)
  FROM sessions JOIN games ON games.id = sessions.game_id
  GROUP BY games.id ORDER BY SUM(sessions.duration) DESC;"
}} > "$EXPORT_DIR/games_summary.txt"
exit 0
"""


# ---------------------------------------------------------------- Lutris
# O Lutris não tem pasta de eventos como o ES-DE: define-se um "Comando
# pré-lançamento" e um "Comando pós-saída" (globais ou por jogo) nas opções de
# Sistema. Os scripts leem variáveis de ambiente que o Lutris expõe:
#   GAME_NAME (antigo: game_name), STORE (loja), GAME_DIRECTORY (pasta).
# A ligação início→fim é feita por um arquivo nomeado pelo nome do jogo
# (sanitizado), o que evita colisões entre jogos diferentes simultâneos.
_SAFE_NAME = (
    'SAFE="$(printf \'%s\' "$NAME" | tr -c \'A-Za-z0-9._-\' \'_\' | cut -c1-120)"'
)


def _lutris_start_script(db_path: Path) -> str:
    rt = _runtime_dir(db_path)
    return f"""#!/usr/bin/env bash
{MARKER}
# Comando PRÉ-LANÇAMENTO do Lutris (opções de Sistema → Comando pré-lançamento).
# Variáveis do Lutris: GAME_NAME (ou game_name), STORE, GAME_DIRECTORY.
set -euo pipefail
RUNTIME_DIR="{rt}"
LOG="$RUNTIME_DIR/tracker.log"
mkdir -p "$RUNTIME_DIR"
{_LOG_FN}
NAME="${{GAME_NAME:-${{game_name:-}}}}"
STORE="${{STORE:-}}"
DIR="${{GAME_DIRECTORY:-}}"
if [ -z "$NAME" ]; then log "ERRO: GAME_NAME ausente no pré-lançamento do Lutris"; exit 0; fi
{_SAFE_NAME}
RUNTIME="$RUNTIME_DIR/lutris_$SAFE"
printf '%s\\n%s\\n%s\\n%s\\n' \\
  "$(date +%Y-%m-%dT%H:%M:%S%z)" "$NAME" "$STORE" "$DIR" > "$RUNTIME"
log "Sessão Lutris iniciada: $NAME [${{STORE:-lutris}}]"
exit 0
"""


def _lutris_end_script(db_path: Path) -> str:
    rt = _runtime_dir(db_path)
    return f"""#!/usr/bin/env bash
{MARKER}
# Comando PÓS-SAÍDA do Lutris (opções de Sistema → Comando pós-saída).
# Lê o início gravado pelo pré-lançamento e insere a sessão no banco do ES-DB.
set -euo pipefail
DB="{db_path}"
RUNTIME_DIR="{rt}"
LOG="$RUNTIME_DIR/tracker.log"
EXPORT="$RUNTIME_DIR/export.sh"
{_LOG_FN}
NAME="${{GAME_NAME:-${{game_name:-}}}}"
if [ -z "$NAME" ]; then exit 0; fi
{_SAFE_NAME}
RUNTIME="$RUNTIME_DIR/lutris_$SAFE"
[ -f "$RUNTIME" ] || exit 0

END="$(date +%Y-%m-%dT%H:%M:%S%z)"
START="$(sed -n '1p' "$RUNTIME")"
NAME="$(sed -n '2p' "$RUNTIME")"
STORE="$(sed -n '3p' "$RUNTIME")"
DIR="$(sed -n '4p' "$RUNTIME")"
rm -f "$RUNTIME"
[ -n "$START" ] && [ -n "$NAME" ] || exit 0

S="$(date -d "$START" +%s 2>/dev/null || echo 0)"
E="$(date -d "$END" +%s 2>/dev/null || echo 0)"
DUR=$(( E - S ))
[ "$DUR" -lt 0 ] && DUR=0

esc() {{ printf "%s" "$1" | sed "s/'/''/g"; }}

# Plataforma exata: consulta o banco do Lutris (pga.db) pela mesma NAME.
#   platform  → já é a plataforma legível quando preenchida (ex.: Windows).
#   runner    → emulador/execução (ex.: duckstation, wine).
#   configpath→ nome do .yml com o core libretro.
LUTRIS_DATA="${{XDG_DATA_HOME:-$HOME/.local/share}}/lutris"
PGA="$LUTRIS_DATA/pga.db"
LPLATFORM=""; LRUNNER=""; LCFG=""; LCORE=""
if [ -f "$PGA" ] && command -v sqlite3 >/dev/null 2>&1; then
  NAME_Q="$(esc "$NAME")"
  ROW="$(sqlite3 -separator '|' "file:$PGA?mode=ro" \\
    "SELECT COALESCE(platform,''), COALESCE(runner,''), COALESCE(configpath,'') \\
     FROM games WHERE name='$NAME_Q' ORDER BY installed DESC, lastplayed DESC LIMIT 1;" \\
    2>/dev/null || true)"
  LPLATFORM="${{ROW%%|*}}"; REST="${{ROW#*|}}"; LRUNNER="${{REST%%|*}}"; LCFG="${{REST##*|}}"
  if [ "$LRUNNER" = "libretro" ] && [ -n "$LCFG" ] && [ -f "$LUTRIS_DATA/games/$LCFG.yml" ]; then
    LCORE="$(sed -n 's/^[[:space:]]*core:[[:space:]]*//p' "$LUTRIS_DATA/games/$LCFG.yml" \\
             | head -1 | tr -d '\\r')"
  fi
fi

# SYSTEM carrega o core (libretro) ou o runner, com marcador lutris: o app
# traduz para o nome de plataforma amigável. PLATFORM guarda o melhor rótulo já
# disponível (plataforma do Lutris, loja, ou genérico) para uso standalone.
if [ -n "$LCORE" ]; then SYSTEM="lutris:$LCORE"
elif [ -n "$LRUNNER" ]; then SYSTEM="lutris:$LRUNNER"
else SYSTEM="lutris"; fi
if [ -n "$LPLATFORM" ]; then PLATFORM="$LPLATFORM"
elif [ -n "$STORE" ]; then PLATFORM="PC — $STORE"
else PLATFORM="PC (Lutris)"; fi

NAME_E="$(esc "$NAME")"
PLATFORM_E="$(esc "$PLATFORM")"
SYSTEM_E="$(esc "$SYSTEM")"
DIR_E="$(esc "$DIR")"

mkdir -p "$(dirname "$DB")"
sqlite3 "$DB" <<SQL
{_SCHEMA_SQL}
INSERT INTO games(name, platform, system, rom) VALUES('$NAME_E','$PLATFORM_E','$SYSTEM_E','$DIR_E')
  ON CONFLICT(name, platform) DO UPDATE SET system=excluded.system, rom=excluded.rom;
INSERT INTO sessions(game_id, start_time, end_time, duration)
  SELECT id, '$START', '$END', $DUR FROM games WHERE name='$NAME_E' AND platform='$PLATFORM_E';
SQL
log "Sessão Lutris encerrada: $NAME [$PLATFORM] (${{DUR}}s)"
[ -x "$EXPORT" ] && "$EXPORT" >/dev/null 2>&1 || true
exit 0
"""


def install_lutris_scripts(target_dir: str | Path, db_path: str | Path) -> list[Path]:
    """Gera os scripts de pré-lançamento/pós-saída do Lutris em ``target_dir``,
    apontando para ``db_path`` (o mesmo banco do ES-DE). Também grava o
    ``export.sh`` na pasta de runtime do ES-DB. O usuário deve apontar, nas
    opções de Sistema do Lutris, o Comando pré-lançamento e o Comando pós-saída
    para os scripts gerados."""
    target = Path(target_dir).expanduser()
    db = Path(db_path).expanduser()
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, body in (("lutris-game-start.sh", _lutris_start_script(db)),
                       ("lutris-game-end.sh", _lutris_end_script(db))):
        path = target / name
        path.write_text(body, encoding="utf-8")
        _chmodx(path)
        written.append(path)
    rt = _runtime_dir(db)
    rt.mkdir(parents=True, exist_ok=True)
    export = rt / "export.sh"
    export.write_text(_export_script(db), encoding="utf-8")
    _chmodx(export)
    return written


def lutris_scripts_installed(target_dir: str | Path) -> bool:
    target = Path(target_dir).expanduser()
    for name in ("lutris-game-start.sh", "lutris-game-end.sh"):
        f = target / name
        try:
            if f.is_file() and MARKER in f.read_text(encoding="utf-8", errors="ignore"):
                return True
        except OSError:
            continue
    return False


def remove_lutris_scripts(target_dir: str | Path) -> list[Path]:
    """Remove apenas os scripts do Lutris gerados pelo ES-DB."""
    target = Path(target_dir).expanduser()
    removed: list[Path] = []
    for name in ("lutris-game-start.sh", "lutris-game-end.sh"):
        f = target / name
        try:
            if f.is_file() and MARKER in f.read_text(encoding="utf-8", errors="ignore"):
                f.unlink()
                removed.append(f)
        except OSError:
            continue
    return removed


def _chmodx(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def install_scripts(scripts_dir: str | Path, db_path: str | Path) -> list[Path]:
    """Instala ``game-start``/``game-end`` no ES-DE e o ``export.sh`` do ES-DB,
    todos apontando para ``db_path`` (adaptação do GameSessionTracker)."""
    scripts = Path(scripts_dir).expanduser()
    db = Path(db_path).expanduser()
    written: list[Path] = []
    for event, body in (("game-start", _start_script(db)),
                        ("game-end", _end_script(db))):
        folder = scripts / event
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / "esdb-tracker.sh"
        target.write_text(body, encoding="utf-8")
        _chmodx(target)
        written.append(target)
    # export.sh vive na pasta do ES-DB (chamado pelo game-end).
    rt = _runtime_dir(db)
    rt.mkdir(parents=True, exist_ok=True)
    export = rt / "export.sh"
    export.write_text(_export_script(db), encoding="utf-8")
    _chmodx(export)
    written.append(export)
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
