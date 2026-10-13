"""Integração com o Heroic Games Launcher.

O Heroic executa os scripts de *before/after launch* **sem** variáveis de
ambiente ou argumentos — só define o diretório de trabalho como a pasta de
instalação do jogo. Então o script identifica o jogo pelo ``$PWD``, cruzando com
as bibliotecas do Heroic (Epic/Legendary, GOG, Amazon/Nile e sideload) para obter
título e loja. A loja vira ``PC (<loja>)`` via :mod:`launchers`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .launchers import pc_platform

# runner do Heroic → chave de loja usada no tag/plataforma.
RUNNER_STORE = {
    "legendary": "epic", "gog": "gog", "nile": "amazon", "sideload": "",
}


def default_heroic_dir() -> Path | None:
    candidates = [
        Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "heroic",
        Path.home() / ".var" / "app" / "com.heroicgameslauncher.hgl"
        / "config" / "heroic",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return None


def platform_from_tag(system: str | None) -> str | None:
    """``heroic:store=<loja>`` → ``PC (<loja>)``."""
    if not system or not str(system).startswith("heroic"):
        return None
    rest = str(system)[len("heroic"):].lstrip(":").strip()
    store = ""
    for part in rest.split(";"):
        if part.startswith("store="):
            store = part.split("=", 1)[1].strip()
    if not store:
        return None
    return pc_platform(store, store)


def _iter_library(path: Path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    games = None
    if isinstance(data, dict):
        for key in ("library", "games"):
            if isinstance(data.get(key), list):
                games = data[key]
                break
    if isinstance(games, list):
        yield from (g for g in games if isinstance(g, dict))


def resolve_by_path(cwd: str, heroic_dir: str | Path | None = None):
    """Dado o diretório de trabalho do jogo, retorna ``(title, store_key)``.

    ``store_key`` é a chave de loja (epic/gog/amazon) ou, para sideload, o SO
    (windows/linux). Retorna ``None`` se nenhum jogo instalado corresponder.
    """
    base = Path(heroic_dir) if heroic_dir else default_heroic_dir()
    if base is None:
        return None
    cwd = str(cwd or "").rstrip("/")
    if not cwd:
        return None
    libs = [
        base / "store_cache" / "legendary_library.json",
        base / "store_cache" / "gog_library.json",
        base / "store_cache" / "nile_library.json",
        base / "sideload_apps" / "library.json",
    ]
    for lib in libs:
        for g in _iter_library(lib):
            if not g.get("is_installed"):
                continue
            install = g.get("install") or {}
            paths = [install.get("install_path"), g.get("folder_name")]
            exe = install.get("executable")
            if exe:
                paths.append(str(Path(exe).parent))
            for p in filter(None, paths):
                p = str(p).rstrip("/")
                if cwd == p or cwd.startswith(p + "/") or p.startswith(cwd + "/"):
                    runner = g.get("runner", "")
                    store = RUNNER_STORE.get(runner, "")
                    if not store:  # sideload: usa o SO declarado
                        store = (install.get("platform") or "Windows").lower()
                        store = "linux" if "linux" in store else "windows"
                    return (g.get("title") or "", store)
    return None
