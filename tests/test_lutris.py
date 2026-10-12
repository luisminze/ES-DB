"""Extração da plataforma exata de jogos do Lutris (pga.db + core libretro)."""

import os
import sqlite3
import subprocess
from pathlib import Path

from esdb.esde.lutris import friendly_platform
from esdb.esde.writer import install_lutris_scripts


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
    conn.commit()
    conn.close()
    (ldir / "games" / "z.yml").write_text(
        "game:\n  core: mupen64plus_next\nrunner: libretro\n")


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
