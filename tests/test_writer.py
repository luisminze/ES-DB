"""Testes da gravação ES-DE: criação de banco e scripts (ESDE.md §5, §7)."""

import sqlite3

import pytest

from esdb.esde.writer import (MARKER, clear_all_data, clear_game_data,
                              create_database, install_lutris_scripts,
                              install_scripts, lutris_scripts_installed,
                              remove_lutris_scripts, remove_scripts,
                              scripts_installed)


def _seed(db):
    conn = sqlite3.connect(str(db))
    conn.execute("INSERT INTO games(id,name,platform) VALUES(1,'A','PC'),(2,'B','PC')")
    conn.execute("INSERT INTO sessions(game_id,start_time,end_time,duration) "
                 "VALUES(1,'x','y',10),(1,'x','y',20),(2,'x','y',5)")
    conn.commit()
    conn.close()


def test_clear_game_data(tmp_path):
    db = create_database(tmp_path / "s.db")
    _seed(db)
    assert clear_game_data(db, 1) is True
    conn = sqlite3.connect(str(db))
    assert conn.execute("SELECT COUNT(*) FROM games").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1
    assert conn.execute("SELECT id FROM games").fetchone()[0] == 2
    conn.close()
    # jogo inexistente não apaga nada
    assert clear_game_data(db, 999) is False


def test_clear_all_data(tmp_path):
    db = create_database(tmp_path / "s.db")
    _seed(db)
    assert clear_all_data(db) is True
    conn = sqlite3.connect(str(db))
    assert conn.execute("SELECT COUNT(*) FROM games").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
    conn.close()


def test_clear_missing_db(tmp_path):
    assert clear_game_data(tmp_path / "nope.db", 1) is False
    assert clear_all_data(tmp_path / "nope.db") is False


def test_create_database_schema(tmp_path):
    db = create_database(tmp_path / "Perfil.db")
    conn = sqlite3.connect(str(db))
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert {"games", "sessions"} <= tables


def test_create_database_never_overwrites(tmp_path):
    db = create_database(tmp_path / "Perfil.db")
    with pytest.raises(FileExistsError):
        create_database(db)
    # com overwrite explícito, aceita
    assert create_database(db, overwrite=True) == db


def test_install_and_remove_scripts(tmp_path):
    scripts = tmp_path / "ES-DE" / "scripts"
    db = tmp_path / "DB" / "Perfil.db"
    written = install_scripts(scripts, db)
    assert len(written) == 3            # game-start, game-end e export.sh
    assert scripts_installed(scripts)
    end = scripts / "game-end" / "esdb-tracker.sh"
    content = end.read_text()
    assert MARKER in content and str(db) in content
    assert "ps2) PLATFORM='Sony PlayStation 2'" in content
    assert end.stat().st_mode & 0o111            # executável
    # export.sh gerado na pasta do banco (.gametracker)
    export = db.parent / ".gametracker" / "export.sh"
    assert export.is_file() and MARKER in export.read_text()
    assert "sessions.csv" in export.read_text()

    # um script de terceiros deve ser preservado na remoção
    other = scripts / "game-start" / "outro.sh"
    other.write_text("#!/bin/bash\necho ola\n")
    removed = remove_scripts(scripts)
    assert len(removed) == 2
    assert other.exists()
    assert not scripts_installed(scripts)


def test_start_script_escapes(tmp_path):
    scripts = tmp_path / "scripts"
    db = tmp_path / "x.db"
    install_scripts(scripts, db)
    start = (scripts / "game-start" / "esdb-tracker.sh").read_text()
    assert "%Y-%m-%dT%H:%M:%S%z" in start


def test_install_and_remove_lutris_scripts(tmp_path):
    target = tmp_path / "lutris"
    db = tmp_path / "database" / "games.db"
    written = install_lutris_scripts(target, db)
    assert len(written) == 2
    names = {p.name for p in written}
    assert names == {"lutris-game-start.sh", "lutris-game-end.sh"}
    assert lutris_scripts_installed(target)
    end = (target / "lutris-game-end.sh").read_text()
    assert MARKER in end and str(db) in end
    assert "GAME_NAME" in end and "PC (Lutris)" in end
    assert (target / "lutris-game-start.sh").stat().st_mode & 0o111
    # export.sh também é gerado na pasta de runtime do banco
    assert (db.parent / ".gametracker" / "export.sh").is_file()

    removed = remove_lutris_scripts(target)
    assert len(removed) == 2
    assert not lutris_scripts_installed(target)


def test_lutris_end_script_records_session(tmp_path):
    """Simula um lançamento do Lutris (variáveis de ambiente) e verifica o banco."""
    import os
    import subprocess

    target = tmp_path / "lutris"
    db = tmp_path / "database" / "games.db"
    start, end = install_lutris_scripts(target, db)
    env = dict(os.environ, GAME_NAME="Hollow Knight", STORE="gog",
               GAME_DIRECTORY="/games/hk")
    subprocess.run(["bash", str(start)], env=env, check=True)
    subprocess.run(["bash", str(end)], env=env, check=True)
    conn = sqlite3.connect(str(db))
    try:
        game = conn.execute(
            "SELECT name, platform, system FROM games").fetchone()
        count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    finally:
        conn.close()
    assert game == ("Hollow Knight", "PC — gog", "lutris")
    assert count == 1
