"""Edição local: overrides de jogo, edição de sessão e wrapper do Heroic."""

import os
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from esdb.data.derived_store import DerivedStore
from esdb.data.library import Library
from esdb.esde.writer import (create_database, install_heroic_scripts,
                              update_session_row)


def test_override_fields(tmp_path):
    st = DerivedStore(tmp_path / "d.db")
    st.set_override("src", 1, title="Novo", platform="PC (Steam)")
    st.set_override("src", 1, rating=0.8)  # mescla, preserva title/platform
    ov = st.get_overrides("src")[1]
    assert ov["title"] == "Novo" and ov["platform"] == "PC (Steam)"
    assert ov["rating"] == 0.8
    st.close()


def _lib(tmp_path):
    db = create_database(tmp_path / "s.db")
    conn = sqlite3.connect(str(db))
    conn.execute("INSERT INTO games(id,name,platform,system,rom) "
                 "VALUES(1,'Jogo','PC (Windows)','heroic:store=windows','')")
    conn.execute("INSERT INTO sessions(id,game_id,start_time,end_time,duration) "
                 "VALUES(5,1,'2026-01-01T10:00:00+00:00','2026-01-01T10:30:00+00:00',1800)")
    conn.commit()
    conn.close()
    lib = Library(str(db), "", timezone.utc, str(tmp_path / "der.db"))
    lib.load()
    return lib, db


def test_edit_game_and_session(tmp_path):
    lib, db = _lib(tmp_path)
    lib.edit_game(1, title="Meu Jogo", platform="PC (Steam)",
                  description="nova", rating=0.6)
    g = lib.games_by_id[1]
    assert g.display_title == "Meu Jogo" and g.platform == "PC (Steam)"
    assert g.metadata.description == "nova" and abs(g.metadata.rating - 0.6) < 1e-9
    # editar sessão: 1h
    dur = lib.update_session(5, datetime(2026, 1, 1, 10, tzinfo=timezone.utc),
                             datetime(2026, 1, 1, 11, tzinfo=timezone.utc))
    assert dur == 3600
    assert lib.games_by_id[1].total_seconds == 3600
    conn = sqlite3.connect(str(db))
    assert conn.execute("SELECT duration FROM sessions WHERE id=5").fetchone()[0] == 3600
    conn.close()


def test_update_session_missing(tmp_path):
    assert update_session_row(tmp_path / "nope.db", 1, "a", "b", 10) is False


def test_heroic_wrapper_records(tmp_path):
    """O wrapper identifica o jogo por HEROIC_APP_NAME e grava a sessão ao fim."""
    hdir = tmp_path / "heroic"
    (hdir / "sideload_apps").mkdir(parents=True)
    (hdir / "store_cache").mkdir()
    import json
    json.dump({"games": [{"runner": "sideload", "app_name": "APP1",
                          "title": "Jogo X", "is_installed": True,
                          "folder_name": str(tmp_path), "install": {"platform": "Windows"}}]},
              open(hdir / "sideload_apps" / "library.json", "w"))
    for n in ("legendary_library", "gog_library", "nile_library"):
        json.dump({"library": []}, open(hdir / "store_cache" / f"{n}.json", "w"))
    db = tmp_path / "database" / "games.db"
    (wrapper,) = install_heroic_scripts(tmp_path / "hs", db, hdir)
    env = dict(os.environ, HEROIC_CONFIG_DIR=str(hdir), HEROIC_APP_NAME="APP1",
               HEROIC_APP_RUNNER="sideload", HEROIC_APP_SOURCE="")
    rc = subprocess.run(["bash", str(wrapper), "true"], env=env)
    assert rc.returncode == 0
    conn = sqlite3.connect(str(db))
    row = conn.execute("SELECT name, platform, system FROM games").fetchone()
    conn.close()
    assert row == ("Jogo X", "PC (Windows)", "heroic:store=windows")


def test_heroic_wrapper_uses_games_map(tmp_path):
    """O wrapper identifica pelo mapa games.json (executável → jogo)."""
    import json
    hdir = tmp_path / "heroic"
    (hdir / "sideload_apps").mkdir(parents=True)
    (hdir / "store_cache").mkdir()
    for n in ("legendary_library", "gog_library", "nile_library"):
        json.dump({"library": []}, open(hdir / "store_cache" / f"{n}.json", "w"))
    json.dump({"games": []}, open(hdir / "sideload_apps" / "library.json", "w"))
    db = tmp_path / "database" / "games.db"
    scripts = tmp_path / "hs"
    (wrapper,) = install_heroic_scripts(scripts, db, hdir)
    # mapa manual: executável -> jogo/plataforma
    json.dump({"meujogo.exe": {"name": "Meu Jogo", "platform": "PC (Epic Games)"}},
              open(scripts / "games.json", "w"))
    env = dict(os.environ, HEROIC_CONFIG_DIR=str(hdir))
    env.pop("HEROIC_APP_NAME", None)
    rc = subprocess.run(
        ["bash", str(wrapper), "true", "C:/x/MeuJogo.exe"], env=env)
    assert rc.returncode == 0
    conn = sqlite3.connect(str(db))
    row = conn.execute("SELECT name, platform FROM games").fetchone()
    conn.close()
    assert row == ("Meu Jogo", "PC (Epic Games)")


def test_delete_and_recalc_session(tmp_path):
    from esdb.esde.writer import delete_session_row, recalc_sessions
    db = create_database(tmp_path / "s.db")
    conn = sqlite3.connect(str(db))
    conn.execute("INSERT INTO games(id,name,platform) VALUES(1,'J','PC (Windows)')")
    # duração gravada 'errada' (10) mas horários indicam 1800s
    conn.execute("INSERT INTO sessions(id,game_id,start_time,end_time,duration) "
                 "VALUES(5,1,'2026-01-01T10:00:00+00:00','2026-01-01T10:30:00+00:00',10),"
                 "(6,1,'2026-01-02T10:00:00+00:00','2026-01-02T10:10:00+00:00',600)")
    conn.commit(); conn.close()
    assert recalc_sessions(db, 1) == 1800 + 600  # sincroniza pelos horários
    assert delete_session_row(db, 6) is True
    conn = sqlite3.connect(str(db))
    assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1
    assert conn.execute("SELECT duration FROM sessions WHERE id=5").fetchone()[0] == 1800
    conn.close()
