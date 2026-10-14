#!/usr/bin/env python3
"""Gera a versão **limpa, só scripts** (sem o programa) em ``standalone/dist/``.

Extrai apenas a lógica de gravação — hooks do ES-DE, Lutris e o wrapper do Heroic
— em scripts bash autossuficientes (só dependem de ``sqlite3`` + ``python3`` da
stdlib). As plataformas são resolvidas com os **mesmos mapas do app**, embutidos
nos scripts, para as integrações ficarem idênticas.

Banco padrão: ``~/Database/Games.db`` (sobreponível por ``GAMES_DB``).

Uso:  python3 standalone/build.py
"""
from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT.parent / "src"
sys.path.insert(0, str(SRC))

from esdb.esde import launchers, lutris, writer  # noqa: E402

OUT = ROOT / "dist"
SCHEMA = writer._SCHEMA_SQL

# Mapas do app embutidos (para os scripts resolverem plataforma sem o programa).
LUTRIS_MAPS = json.dumps({
    "core": lutris.CORE_PLATFORM,
    "emu": lutris.EMULATOR_RUNNER_PLATFORM,
    "store": launchers.STORE_PLATFORM,
}, ensure_ascii=False)

# case bash sistema→plataforma (ES-DE), espelhando PLATFORM_MAP.
ESDE_CASE = "\n".join(
    [f"    {k}) PLATFORM='{v}' ;;" for k, v in writer.PLATFORM_MAP.items()]
    + ["    *) PLATFORM=\"$SYSTEM\" ;;"])

HEADER = """#!/usr/bin/env bash
# ======================================================================
# ActivityPlayTime — versão LIMPA (somente scripts). Gerado por build.py.
# Banco: ${GAMES_DB:-$HOME/Database/Games.db}
# Requer: sqlite3, python3 (stdlib), date (GNU). Sem rede.
# ======================================================================
"""

COMMON = r"""set -uo pipefail
DB="${GAMES_DB:-$HOME/Database/Games.db}"
RUNTIME_DIR="${GAMES_RUNTIME:-$HOME/Database/.gametracker}"
EXPORT_SH="$RUNTIME_DIR/export.sh"
LOG="$RUNTIME_DIR/tracker.log"
mkdir -p "$RUNTIME_DIR" "$(dirname "$DB")"
log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$LOG"; }
esc() { printf "%s" "$1" | sed "s/'/''/g"; }
"""

# Bloco de INSERT compartilhado (usa $NAME_E $PLATFORM_E $SYSTEM_E $ROM_E
# $START $END $DUR já definidos).
RECORD = f"""sqlite3 "$DB" <<SQL
{SCHEMA}
INSERT INTO games(name, platform, system, rom)
  VALUES('$NAME_E','$PLATFORM_E','$SYSTEM_E','$ROM_E')
  ON CONFLICT(name, platform) DO UPDATE SET system=excluded.system, rom=excluded.rom;
INSERT INTO sessions(game_id, start_time, end_time, duration)
  SELECT id, '$START', '$END', $DUR FROM games
  WHERE name='$NAME_E' AND platform='$PLATFORM_E';
SQL
[ -x "$EXPORT_SH" ] && "$EXPORT_SH" >/dev/null 2>&1 || true
"""


def _w(relpath: str, text: str, executable: bool = True) -> None:
    p = OUT / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    if executable:
        p.chmod(p.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    print("gerado:", p.relative_to(ROOT))


# ------------------------------------------------------------------ ES-DE
def esde_start() -> str:
    return HEADER + """# ES-DE game-start. Args: $1=ROM $2=NOME $3=SISTEMA $4=PLATAFORMA
""" + COMMON + r"""
RUNTIME="$RUNTIME_DIR/current_session"
ROM="${1:-}"; NAME="${2:-}"; SYSTEM="${3:-}"; PLATFORM="${4:-}"
if [ -z "$NAME" ]; then log "ES-DE: nome ausente no game-start"; exit 0; fi
printf '%s\n%s\n%s\n%s\n%s\n' \
  "$(date +%Y-%m-%dT%H:%M:%S%z)" "$NAME" "$SYSTEM" "$PLATFORM" "$ROM" > "$RUNTIME"
log "ES-DE iniciado: $NAME [${PLATFORM:-$SYSTEM}]"
exit 0
"""


def esde_end() -> str:
    return HEADER + "# ES-DE game-end: lê o início e grava a sessão.\n" + COMMON + f"""
RUNTIME="$RUNTIME_DIR/current_session"
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
DUR=$(( E - S )); [ "$DUR" -lt 0 ] && DUR=0
if [ -z "$PLATFORM" ]; then
  case "$SYSTEM" in
{ESDE_CASE}
  esac
fi
NAME_E="$(esc "$NAME")"; PLATFORM_E="$(esc "$PLATFORM")"
SYSTEM_E="$(esc "$SYSTEM")"; ROM_E="$(esc "$ROM")"
{RECORD}log "ES-DE encerrado: $NAME [$PLATFORM] (${{DUR}}s)"
exit 0
"""


# ----------------------------------------------------------------- Lutris
def lutris_start() -> str:
    return HEADER + """# Lutris pré-lançamento. Variáveis: GAME_NAME, STORE, GAME_DIRECTORY.
""" + COMMON + r"""
NAME="${GAME_NAME:-${game_name:-}}"
STORE="${STORE:-}"; DIR="${GAME_DIRECTORY:-}"
if [ -z "$NAME" ]; then log "Lutris: GAME_NAME ausente"; exit 0; fi
SAFE="$(printf '%s' "$NAME" | tr -c 'A-Za-z0-9._-' '_' | cut -c1-120)"
RUNTIME="$RUNTIME_DIR/lutris_$SAFE"
printf '%s\n%s\n%s\n%s\n' "$(date +%Y-%m-%dT%H:%M:%S%z)" "$NAME" "$STORE" "$DIR" > "$RUNTIME"
log "Lutris iniciado: $NAME [${STORE:-lutris}]"
exit 0
"""


_LUTRIS_PY = r"""
import json, sys
M = json.loads(r'''%s''')
CORE, EMU, STORE = M["core"], M["emu"], M["store"]
runner = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
core = (sys.argv[2] if len(sys.argv) > 2 else "").strip()
store = (sys.argv[3] if len(sys.argv) > 3 else "").strip().lower()
pga = (sys.argv[4] if len(sys.argv) > 4 else "").strip()
def pc(store, os_hint):
    if store in STORE:
        return STORE[store]
    return "PC (Linux)" if os_hint == "linux" else "PC (Windows)"
if core and core in CORE:
    print(CORE[core]); sys.exit()
if core:
    print("RetroArch: " + core); sys.exit()
if runner in EMU:
    print(EMU[runner]); sys.exit()
if pga and pga not in ("Windows", "Linux"):
    print(pga); sys.exit()
os_hint = "linux" if (runner in ("linux", "flatpak") or pga == "Linux") else "windows"
s = store or ("steam" if runner == "steam" else "")
print(pc(s, os_hint))
""" % LUTRIS_MAPS


def lutris_end() -> str:
    return HEADER + "# Lutris pós-saída: resolve a plataforma exata e grava.\n" + COMMON + f"""
NAME="${{GAME_NAME:-${{game_name:-}}}}"
[ -n "$NAME" ] || exit 0
SAFE="$(printf '%s' "$NAME" | tr -c 'A-Za-z0-9._-' '_' | cut -c1-120)"
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
DUR=$(( E - S )); [ "$DUR" -lt 0 ] && DUR=0

# Descobre runner/core (desambigua wine x emulador pelo WINEPREFIX).
LUTRIS_DATA="${{XDG_DATA_HOME:-$HOME/.local/share}}/lutris"
PGA="$LUTRIS_DATA/pga.db"
LRUNNER=""; LCFG=""; LCORE=""; LPLAT=""
if [ -n "${{WINEPREFIX:-}}" ]; then
  LRUNNER="wine"
elif [ -f "$PGA" ] && command -v sqlite3 >/dev/null 2>&1; then
  NAME_Q="$(esc "$NAME")"
  ROW="$(sqlite3 -separator '|' "file:$PGA?mode=ro" \\
    "SELECT COALESCE(runner,''), COALESCE(configpath,''), COALESCE(platform,'') \\
     FROM games WHERE name='$NAME_Q' AND COALESCE(runner,'')<>'wine' \\
     ORDER BY installed DESC, lastplayed DESC LIMIT 1;" 2>/dev/null || true)"
  LRUNNER="${{ROW%%|*}}"; REST="${{ROW#*|}}"; LCFG="${{REST%%|*}}"; LPLAT="${{REST##*|}}"
  if [ "$LRUNNER" = "libretro" ] && [ -n "$LCFG" ] && [ -f "$LUTRIS_DATA/games/$LCFG.yml" ]; then
    LCORE="$(sed -n 's/^[[:space:]]*core:[[:space:]]*//p' "$LUTRIS_DATA/games/$LCFG.yml" | head -1 | tr -d '\\r')"
  fi
fi
PLATFORM="$(python3 -I - "$LRUNNER" "$LCORE" "$STORE" "$LPLAT" <<'PYEOF'
{_LUTRIS_PY}
PYEOF
)"
[ -n "$PLATFORM" ] || PLATFORM="PC (Windows)"
SYSTEM="lutris:runner=$LRUNNER;core=$LCORE;store=$STORE"
NAME_E="$(esc "$NAME")"; PLATFORM_E="$(esc "$PLATFORM")"
SYSTEM_E="$(esc "$SYSTEM")"; ROM_E="$(esc "$DIR")"
{RECORD}log "Lutris encerrado: $NAME [$PLATFORM] (${{DUR}}s)"
exit 0
"""


# ----------------------------------------------------------------- Heroic
_HEROIC_PY = r"""
import json, sys
from pathlib import Path
args = sys.argv[1:]
map_path = args[0] if len(args) > 0 else ""
base = Path(args[1]) if len(args) > 1 and args[1] else None
app = args[2] if len(args) > 2 else ""
source = (args[3] if len(args) > 3 else "").lower()
runner = (args[4] if len(args) > 4 else "").lower()
cmd = args[5:]
LABEL = {"steam": "PC (Steam)", "gog": "PC (GOG)", "epic": "PC (Epic Games)",
         "egs": "PC (Epic Games)", "amazon": "PC (Amazon)", "nile": "PC (Amazon)",
         "linux": "PC (Linux)", "windows": "PC (Windows)"}
def label(store):
    return LABEL.get(store, "PC (Linux)" if store == "linux" else "PC (Windows)")
def bases(c):
    out = []
    for a in c:
        s = str(a).replace("\\", "/")
        if "/" in s or s.lower().endswith(".exe"):
            out.append(Path(s).name.lower())
    return out
try:
    gmap = json.load(open(map_path))
except Exception:
    gmap = {}
for bn in bases(cmd):
    e = gmap.get(bn)
    if isinstance(e, dict) and e.get("name"):
        sys.stdout.write(e["name"] + "\t" + (e.get("platform") or "PC (Windows)") + "\t")
        sys.exit(0)
    if isinstance(e, str) and e:
        sys.stdout.write(e + "\tPC (Windows)\t"); sys.exit(0)
def load(p):
    try:
        d = json.load(open(p))
    except Exception:
        return []
    if isinstance(d, dict):
        for k in ("library", "games"):
            if isinstance(d.get(k), list):
                return [g for g in d[k] if isinstance(g, dict)]
    return []
entries = []
if base:
    for nm in ("store_cache/legendary_library.json", "store_cache/gog_library.json",
               "store_cache/nile_library.json", "sideload_apps/library.json"):
        entries += load(base / nm)
RS = {"legendary": "epic", "gog": "gog", "nile": "amazon"}
SRC = {"epic": "epic", "gog": "gog", "amazon": "amazon", "nile": "amazon"}
def store_for(g):
    st = RS.get(g.get("runner", ""), "") or RS.get(runner, "") or SRC.get(source, "")
    if not st:
        pl = ((g.get("install") or {}).get("platform") or "Windows").lower()
        st = "linux" if "linux" in pl else "windows"
    return st
title = ""; store = ""
if app:
    for g in entries:
        if g.get("app_name") == app:
            title, store = g.get("title") or "", store_for(g); break
if not title and cmd:
    norm = [str(a).replace("\\", "/").rstrip("/") for a in cmd
            if ("/" in str(a) or str(a).lower().endswith(".exe"))]
    for g in entries:
        ins = g.get("install") or {}
        exe = ins.get("executable")
        paths = [str(p).replace("\\", "/").rstrip("/")
                 for p in (exe, ins.get("install_path"), g.get("folder_name")) if p]
        eb = Path(str(exe).replace("\\", "/")).name.lower() if exe else ""
        hit = False
        for a in norm:
            ab = Path(a).name.lower()
            for p in paths:
                if a == p or a.startswith(p + "/") or p.startswith(a + "/"):
                    hit = True; break
            if hit or (eb and ab == eb):
                hit = True; break
        if hit:
            title, store = g.get("title") or "", store_for(g); break
if title:
    sys.stdout.write(title + "\t" + label(store) + "\t" + store)
"""


def heroic_wrapper() -> str:
    return HEADER + "# Heroic WRAPPER (Configurações → Avançado → Empacotador).\n" + COMMON + f"""
HEROIC_DIR="${{HEROIC_CONFIG_DIR:-$HOME/.config/heroic}}"
[ -d "$HEROIC_DIR" ] || HEROIC_DIR="$HOME/.var/app/com.heroicgameslauncher.hgl/config/heroic"
MAP="${{HEROIC_MAP:-$HOME/Database/heroic-games.json}}"
APP="${{HEROIC_APP_NAME:-}}"; SOURCE="${{HEROIC_APP_SOURCE:-}}"; RUNNER="${{HEROIC_APP_RUNNER:-}}"
INFO=""
if command -v python3 >/dev/null 2>&1; then
  INFO="$(python3 -I - "$MAP" "$HEROIC_DIR" "$APP" "$SOURCE" "$RUNNER" "$@" <<'PYEOF'
{_HEROIC_PY}
PYEOF
)"
fi
TITLE=""; PLATFORM=""; STORE=""
IFS=$'\\t' read -r TITLE PLATFORM STORE <<EOF
$INFO
EOF
START="$(date +%Y-%m-%dT%H:%M:%S%z)"
if [ "$#" -gt 0 ]; then "$@"; RC=$?; else RC=0; fi
END="$(date +%Y-%m-%dT%H:%M:%S%z)"
if [ -z "$TITLE" ]; then log "Heroic não identificado. APP='$APP' CMD='$*'"; exit $RC; fi
[ -z "$PLATFORM" ] && PLATFORM="PC (Windows)"
if [ -n "$STORE" ]; then SYSTEM="heroic:store=$STORE"; else SYSTEM="heroic"; fi
S="$(date -d "$START" +%s 2>/dev/null || echo 0)"
E="$(date -d "$END" +%s 2>/dev/null || echo 0)"
DUR=$(( E - S )); [ "$DUR" -lt 0 ] && DUR=0
NAME_E="$(esc "$TITLE")"; PLATFORM_E="$(esc "$PLATFORM")"
SYSTEM_E="$(esc "$SYSTEM")"; ROM_E="$(esc "$APP")"
{RECORD}log "Heroic encerrado: $TITLE [$PLATFORM] (${{DUR}}s)"
exit $RC
"""


_HEROIC_MAP_PY = r"""
import json, sys
from pathlib import Path
base = Path(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] else None
out_path = sys.argv[2] if len(sys.argv) > 2 else ""
LABEL = {"epic": "PC (Epic Games)", "gog": "PC (GOG)", "amazon": "PC (Amazon)",
         "windows": "PC (Windows)", "linux": "PC (Linux)"}
RS = {"legendary": "epic", "gog": "gog", "nile": "amazon", "sideload": ""}
def load(p):
    try:
        d = json.load(open(p))
    except Exception:
        return []
    if isinstance(d, dict):
        for k in ("library", "games"):
            if isinstance(d.get(k), list):
                return [g for g in d[k] if isinstance(g, dict)]
    return []
gen = {}
if base:
    for nm in ("store_cache/legendary_library.json", "store_cache/gog_library.json",
               "store_cache/nile_library.json", "sideload_apps/library.json"):
        for g in load(base / nm):
            exe = (g.get("install") or {}).get("executable")
            if not exe:
                continue
            key = Path(str(exe).replace("\\", "/")).name.lower()
            if not key:
                continue
            st = RS.get(g.get("runner", ""), "")
            if not st:
                pl = ((g.get("install") or {}).get("platform") or "Windows").lower()
                st = "linux" if "linux" in pl else "windows"
            gen[key] = {"name": g.get("title") or key,
                        "platform": LABEL.get(st, "PC (Windows)")}
existing = {}
try:
    existing = json.load(open(out_path))
except Exception:
    existing = {}
merged = {**gen, **existing}  # edições do usuário têm prioridade
open(out_path, "w").write(json.dumps(merged, indent=2, ensure_ascii=False))
print(len(merged))
"""


def heroic_genmap() -> str:
    return HEADER + "# Gera/atualiza o mapa Heroic (executável → jogo) em ~/Database.\n" + COMMON + f"""
HEROIC_DIR="${{HEROIC_CONFIG_DIR:-$HOME/.config/heroic}}"
[ -d "$HEROIC_DIR" ] || HEROIC_DIR="$HOME/.var/app/com.heroicgameslauncher.hgl/config/heroic"
MAP="${{HEROIC_MAP:-$HOME/Database/heroic-games.json}}"
N="$(python3 -I - "$HEROIC_DIR" "$MAP" <<'PYEOF'
{_HEROIC_MAP_PY}
PYEOF
)"
echo "Mapa do Heroic: $N jogo(s) em $MAP"
"""


def export_sh() -> str:
    # Reaproveita o export do app (já é bash puro), só troca os caminhos.
    body = writer._export_script(Path("/__DB__")).replace(
        'DB="/__DB__"', 'DB="${GAMES_DB:-$HOME/Database/Games.db}"').replace(
        'EXPORT_DIR="/exports"',
        'EXPORT_DIR="${GAMES_EXPORT:-$HOME/Database/exports}"').replace(
        'LOG="/.gametracker/tracker.log"',
        'LOG="${GAMES_RUNTIME:-$HOME/Database/.gametracker}/tracker.log"')
    # remove o marcador do app e ajusta o cabeçalho
    return body


def install_sh() -> str:
    return HEADER + r"""# Instalador da versão limpa (só scripts).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB="${GAMES_DB:-$HOME/Database/Games.db}"
RUNTIME_DIR="${GAMES_RUNTIME:-$HOME/Database/.gametracker}"
mkdir -p "$(dirname "$DB")" "$RUNTIME_DIR"

# 1) Cria o banco (se não existir) com o esquema.
sqlite3 "$DB" < "$HERE/schema.sql"
echo "Banco: $DB"

# 2) Instala o export na pasta de runtime (chamado após cada sessão).
install -m755 "$HERE/export.sh" "$RUNTIME_DIR/export.sh"

echo
echo "Scripts prontos em: $HERE"
echo
echo "== ES-DE =="
echo "  copie esde/game-start.sh  -> <ES-DE>/scripts/game-start/"
echo "  copie esde/game-end.sh    -> <ES-DE>/scripts/game-end/"
echo "  (e ative 'Enable Custom Event Scripts' no ES-DE)"
echo
echo "== Lutris (opções de Sistema, global ou por jogo) =="
echo "  Comando pré-lançamento = $HERE/lutris/lutris-game-start.sh"
echo "  Comando pós-saída      = $HERE/lutris/lutris-game-end.sh"
echo
echo "== Heroic (Configurações → Avançado → Empacotador, global/por jogo) =="
echo "  Empacotador = $HERE/heroic/heroic-wrapper.sh   (Argumentos em branco)"
echo "  Gere o mapa:  $HERE/heroic/gen-heroic-map.sh"
echo "  (jogos com config própria precisam do Empacotador neles também)"
"""


README = """# ActivityPlayTime — versão limpa (somente scripts)

Grava o tempo de jogo de **ES-DE, Lutris e Heroic** num SQLite, **sem** nenhum
programa/GUI — apenas scripts `bash` (+ `python3` da stdlib e `sqlite3`).

- **Banco:** `~/Database/Games.db` (sobreponível por `GAMES_DB`).
- **Runtime/log:** `~/Database/.gametracker/`  ·  **Exports:** `~/Database/exports/`
- **Mapa do Heroic:** `~/Database/heroic-games.json` (editável).

## Instalar
```bash
bash install.sh
```
Cria o banco e imprime onde apontar cada launcher. Resumo:

| Launcher | Onde configurar | Script |
|---|---|---|
| ES-DE | copiar para `<ES-DE>/scripts/game-{start,end}/` | `esde/game-start.sh`, `esde/game-end.sh` |
| Lutris | Opções de Sistema → pré-lançamento / pós-saída | `lutris/lutris-game-start.sh`, `lutris/lutris-game-end.sh` |
| Heroic | Avançado → Empacotador (global e por jogo) | `heroic/heroic-wrapper.sh` |

Heroic: rode `heroic/gen-heroic-map.sh` para (re)criar o mapa executável→jogo.

## Esquema (`Games.db`)
- `games(id, name, platform, system, rom, UNIQUE(name, platform))`
- `sessions(id, game_id, start_time, end_time, duration)`

Plataformas são resolvidas como no app completo (consoles e PC por loja:
Windows/Steam/Epic/GOG/Amazon/Linux); o mesmo título em plataformas diferentes
nunca se mistura.
"""


def main() -> int:
    if OUT.exists():
        for p in sorted(OUT.rglob("*"), reverse=True):
            p.unlink() if p.is_file() else p.rmdir()
    _w("schema.sql", SCHEMA, executable=False)
    _w("esde/game-start.sh", esde_start())
    _w("esde/game-end.sh", esde_end())
    _w("lutris/lutris-game-start.sh", lutris_start())
    _w("lutris/lutris-game-end.sh", lutris_end())
    _w("heroic/heroic-wrapper.sh", heroic_wrapper())
    _w("heroic/gen-heroic-map.sh", heroic_genmap())
    _w("export.sh", export_sh())
    _w("install.sh", install_sh())
    _w("README.md", README, executable=False)
    print("\nOK -> " + str(OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
