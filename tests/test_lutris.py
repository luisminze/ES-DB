"""Extração da plataforma exata de jogos do Lutris (pga.db + core libretro)."""

import os
import sqlite3
import subprocess
from pathlib import Path

from esdb.esde.lutris import LutrisIndex, friendly_platform
from esdb.esde.writer import (create_database, install_lutris_scripts,
                              sync_lutris_rows)


def test_friendly_platform_core_and_runner():
    assert friendly_platform("lutris:mupen64plus_next", "x") == "Nintendo 64"
    assert friendly_platform("lutris:mgba", "x") == "Nintendo Game Boy Advance"
    assert friendly_platform("lutris:duckstation", "x") == "Sony PlayStation"
    assert friendly_platform("lutris:wine", "x") == "Windows"


def test_friendly_platform_fallbacks():
    # tag desconhecido mantém o rótulo armazenado
    assert friendly_platform("lutris:algo_novo", "Windows") == "Windows"
    # sem tag, usa fallback (ou genérico)
    assert friendly_platform("lutris", "PC (Lutris)") == "PC (Lutris)"
    # jogo que não é do Lutris não é tocado
    assert friendly_platform("ps2", "Sony PlayStation 2") == "Sony PlayStation 2"


def _fake_lutris(xdg: Path) -> None:
    ldir = xdg / "lutris"
    (ldir / "games").mkdir(parents=True)
    conn = sqlite3.connect(str(ldir / "pga.db"))
    conn.execute("CREATE TABLE games(id INTEGER PRIMARY KEY, name TEXT, "
                 "platform TEXT, runner TEXT, configpath TEXT, installed INTEGER, "
                 "lastplayed INTEGER)")
    conn.execute("INSERT INTO games VALUES(1,'Zero Hour','','libretro','z',1,1)")
    conn.execute("INSERT INTO games VALUES(2,'Forza','Windows','wine','',1,2)")
    conn.execute("INSERT INTO games VALUES(3,'RE3','Sony PlayStation','duckstation','',1,3)")
    conn.commit()
    conn.close()
    (ldir / "games" / "z.yml").write_text(
        "game:\n  core: mupen64plus_next\nrunner: libretro\n")


def test_index_system_tag(tmp_path):
    _fake_lutris(tmp_path)
    idx = LutrisIndex(tmp_path / "lutris")
    assert idx.system_tag_for("Zero Hour") == "lutris:mupen64plus_next"
    assert idx.system_tag_for("RE3") == "lutris:duckstation"
    assert idx.platform_for("RE3") == "Sony PlayStation"


def test_sync_lutris_rows_fixes_generic_platform(tmp_path):
    _fake_lutris(tmp_path)
    db = create_database(tmp_path / "games.db")
    conn = sqlite3.connect(str(db))
    conn.execute("INSERT INTO games(id,name,platform,system) "
                 "VALUES(10,'RE3','PC (Lutris)','lutris')")
    conn.execute("INSERT INTO sessions(game_id,start_time,end_time,duration) "
                 "VALUES(10,'a','b',60)")
    conn.commit()
    conn.close()
    n = sync_lutris_rows(db, tmp_path / "lutris")
    assert n == 1
    conn = sqlite3.connect(str(db))
    row = conn.execute("SELECT platform, system FROM games WHERE id=10").fetchone()
    conn.close()
    assert row == ("Sony PlayStation", "lutris:duckstation")
    # idempotente: segunda passada não muda nada
    assert sync_lutris_rows(db, tmp_path / "lutris") == 0


def test_sync_lutris_rows_merges_duplicates(tmp_path):
    _fake_lutris(tmp_path)
    db = create_database(tmp_path / "games.db")
    conn = sqlite3.connect(str(db))
    # linha antiga genérica + linha exata já existente, mesmo nome
    conn.execute("INSERT INTO games(id,name,platform,system) "
                 "VALUES(10,'RE3','PC (Lutris)','lutris')")
    conn.execute("INSERT INTO games(id,name,platform,system) "
                 "VALUES(11,'RE3','Sony PlayStation','lutris:duckstation')")
    conn.execute("INSERT INTO sessions(game_id,start_time,end_time,duration) "
                 "VALUES(10,'a','b',60),(11,'c','d',30)")
    conn.commit()
    conn.close()
    assert sync_lutris_rows(db, tmp_path / "lutris") == 1
    conn = sqlite3.connect(str(db))
    games = conn.execute("SELECT COUNT(*) FROM games WHERE name='RE3'").fetchone()[0]
    sess = conn.execute("SELECT COUNT(*) FROM sessions WHERE game_id=11").fetchone()[0]
    conn.close()
    assert games == 1 and sess == 2  # as duas sessões ficam no jogo exato


def test_end_script_extracts_platform_from_pga(tmp_path):
    xdg = tmp_path / "xdg"
    _fake_lutris(xdg)
    db = tmp_path / "database" / "games.db"
    start, end = install_lutris_scripts(tmp_path / "scripts", db)
    env = dict(os.environ, XDG_DATA_HOME=str(xdg))
    for name in ("Zero Hour", "Forza"):
        e = dict(env, GAME_NAME=name)
        subprocess.run(["bash", str(start)], env=e, check=True)
        subprocess.run(["bash", str(end)], env=e, check=True)
    conn = sqlite3.connect(str(db))
    rows = dict((n, (p, s)) for n, p, s in
                conn.execute("SELECT name, platform, system FROM games"))
    conn.close()
    # libretro sem plataforma no pga.db → core vira o system; app traduz p/ N64
    assert rows["Zero Hour"][1] == "lutris:mupen64plus_next"
    assert friendly_platform(rows["Zero Hour"][1], rows["Zero Hour"][0]) == "Nintendo 64"
    # wine com plataforma preenchida no pga.db → grava "Windows"
    assert rows["Forza"][0] == "Windows"
    assert friendly_platform(rows["Forza"][1], rows["Forza"][0]) == "Windows"
