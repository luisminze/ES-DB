"""Plataforma por launcher (Lutris/Heroic): tags sem ambiguidade de nome."""

import json
import os
import sqlite3
import subprocess
from pathlib import Path

from esdb.esde.heroic import platform_from_tag as heroic_platform
from esdb.esde.heroic import resolve_by_path
from esdb.esde.lutris import platform_from_tag
from esdb.esde.writer import (create_database, install_heroic_scripts,
                              install_lutris_scripts, sync_launcher_rows)


def test_lutris_platform_from_tag():
    assert platform_from_tag("lutris:runner=libretro;core=mupen64plus_next;store=") \
        == "Nintendo 64"
    assert platform_from_tag("lutris:runner=xenia;core=;store=") == "Microsoft Xbox 360"
    assert platform_from_tag("lutris:runner=wine;core=;store=") == "PC (Windows)"
    assert platform_from_tag("lutris:runner=wine;core=;store=steam") == "PC (Steam)"
    assert platform_from_tag("lutris:runner=linux;core=;store=") == "PC (Linux)"
    # legado (token único)
    assert platform_from_tag("lutris:duckstation") == "Sony PlayStation"
    assert platform_from_tag("lutris:wine") == "PC (Windows)"
    # jogo não-lutris é ignorado
    assert platform_from_tag("xbox360") is None


def test_heroic_platform_from_tag():
    assert heroic_platform("heroic:store=epic") == "PC (Epic Games)"
    assert heroic_platform("heroic:store=gog") == "PC (GOG)"
    assert heroic_platform("heroic:store=amazon") == "PC (Amazon)"
    assert heroic_platform("heroic:store=windows") == "PC (Windows)"
    assert heroic_platform("lutris:wine") is None


def test_heroic_resolve_by_path(tmp_path):
    hdir = tmp_path / "heroic"
    (hdir / "sideload_apps").mkdir(parents=True)
    (hdir / "store_cache").mkdir()
    gdir = tmp_path / "games" / "FH2"
    gdir.mkdir(parents=True)
    json.dump({"games": [{"runner": "sideload", "title": "Forza Horizon 2",
                          "is_installed": True, "folder_name": str(gdir),
                          "install": {"platform": "Windows"}}]},
              open(hdir / "sideload_apps" / "library.json", "w"))
    for n in ("legendary_library", "gog_library", "nile_library"):
        json.dump({"library": []}, open(hdir / "store_cache" / f"{n}.json", "w"))
    assert resolve_by_path(str(gdir), hdir) == ("Forza Horizon 2", "windows")
    assert resolve_by_path(str(gdir / "sub"), hdir) == ("Forza Horizon 2", "windows")
    assert resolve_by_path(str(tmp_path / "outro"), hdir) is None


def _fake_lutris_pga(xdg: Path) -> None:
    ldir = xdg / "lutris"
    (ldir / "games").mkdir(parents=True)
    conn = sqlite3.connect(str(ldir / "pga.db"))
    conn.execute("CREATE TABLE games(id INTEGER PRIMARY KEY, name TEXT, "
                 "platform TEXT, runner TEXT, configpath TEXT, installed INTEGER, "
                 "lastplayed INTEGER)")
    # Mesmo nome, duas plataformas (wine e xenia).
    conn.execute("INSERT INTO games VALUES(1,'FH2','Windows','wine','',1,2)")
    conn.execute("INSERT INTO games VALUES(2,'FH2','Microsoft Xbox 360','xenia','',1,5)")
    conn.commit()
    conn.close()


def test_same_name_two_platforms_stay_separate(tmp_path):
    """Forza (wine) e Forza (xenia) não podem virar um só jogo."""
    xdg = tmp_path / "xdg"
    _fake_lutris_pga(xdg)
    db = tmp_path / "database" / "games.db"
    start, end = install_lutris_scripts(tmp_path / "ls", db)
    base = dict(os.environ, XDG_DATA_HOME=str(xdg))
    # wine (WINEPREFIX definido)
    e1 = dict(base, GAME_NAME="FH2", WINEPREFIX=str(tmp_path / "pfx"))
    subprocess.run(["bash", str(start)], env=e1, check=True)
    subprocess.run(["bash", str(end)], env=e1, check=True)
    # xenia (sem WINEPREFIX)
    e2 = dict(base, GAME_NAME="FH2")
    e2.pop("WINEPREFIX", None)
    subprocess.run(["bash", str(start)], env=e2, check=True)
    subprocess.run(["bash", str(end)], env=e2, check=True)
    sync_launcher_rows(db)
    conn = sqlite3.connect(str(db))
    plats = sorted(r[0] for r in conn.execute(
        "SELECT platform FROM games WHERE name='FH2'"))
    conn.close()
    assert plats == ["Microsoft Xbox 360", "PC (Windows)"]


def test_sync_launcher_rows_normalizes_and_merges(tmp_path):
    db = create_database(tmp_path / "games.db")
    conn = sqlite3.connect(str(db))
    # linha com rótulo de escrita feio + linha final já existente, mesmo tag
    conn.execute("INSERT INTO games(id,name,platform,system) VALUES"
                 "(10,'Zelda','Lutris core: mupen64plus_next',"
                 "'lutris:runner=libretro;core=mupen64plus_next;store='),"
                 "(11,'Zelda','Nintendo 64',"
                 "'lutris:runner=libretro;core=mupen64plus_next;store=')")
    conn.execute("INSERT INTO sessions(game_id,start_time,end_time,duration) "
                 "VALUES(10,'a','b',60),(11,'c','d',30)")
    conn.commit()
    conn.close()
    assert sync_launcher_rows(db) == 1
    conn = sqlite3.connect(str(db))
    n = conn.execute("SELECT COUNT(*) FROM games WHERE name='Zelda'").fetchone()[0]
    sess = conn.execute("SELECT COUNT(*) FROM sessions WHERE game_id=11").fetchone()[0]
    conn.close()
    assert n == 1 and sess == 2


def test_heroic_wrapper_injection(tmp_path):
    import json
    from esdb.esde.heroic import install_wrapper_in_game_configs
    gc = tmp_path / "heroic" / "GamesConfig"
    gc.mkdir(parents=True)
    # jogo com config própria SEM wrapper
    (gc / "APP1.json").write_text(json.dumps(
        {"APP1": {"winePrefix": "/x"}, "version": "v0", "explicit": True}))
    # jogo que já tem o wrapper (idempotência)
    w = str(tmp_path / "heroic" / "heroic-wrapper.sh")
    (gc / "APP2.json").write_text(json.dumps(
        {"APP2": {"wrapperOptions": [{"exe": w, "args": ""}]},
         "version": "v0", "explicit": True}))
    (gc / "default.json").write_text("{}")
    updated = install_wrapper_in_game_configs(tmp_path / "heroic", w)
    assert updated == ["APP1"]  # só o que faltava
    d = json.loads((gc / "APP1.json").read_text())
    assert d["APP1"]["wrapperOptions"] == [{"exe": w, "args": ""}]
    # roda de novo: nada muda
    assert install_wrapper_in_game_configs(tmp_path / "heroic", w) == []
