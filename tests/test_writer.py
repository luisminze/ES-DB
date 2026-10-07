"""Testes da gravação ES-DE: criação de banco e scripts (ESDE.md §5, §7)."""

import sqlite3

import pytest

from esdb.esde.writer import (MARKER, create_database, install_scripts,
                              remove_scripts, scripts_installed)


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
    assert len(written) == 2
    assert scripts_installed(scripts)
    end = scripts / "game-end" / "esdb-tracker.sh"
    content = end.read_text()
    assert MARKER in content and str(db) in content
    assert "ps2) PLATFORM='Sony PlayStation 2'" in content
    assert end.stat().st_mode & 0o111            # executável

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
