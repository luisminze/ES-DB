"""Testes do exportador de sessões (porta do export.sh)."""

import sqlite3

from esdb.esde.export import default_export_dir, export_sessions
from esdb.esde.writer import create_database


def _seed(db):
    conn = sqlite3.connect(str(db))
    conn.execute("INSERT INTO games(name,platform,system,rom) "
                 "VALUES('Jogo A','Sony PlayStation 2','ps2','/a.chd')")
    conn.execute("INSERT INTO sessions(game_id,start_time,end_time,duration) "
                 "VALUES(1,'2026-01-01T10:00:00-0300','2026-01-01T11:00:00-0300',3600)")
    conn.commit()
    conn.close()


def test_export_creates_files(tmp_path):
    db = create_database(tmp_path / "database" / "Perfil.db")
    _seed(db)
    out = export_sessions(db)
    # ~/ES-DB/exports equivalente: pasta irmã de database/
    assert out == tmp_path / "exports"
    for name in ("sessions.csv", "sessions.txt",
                 "games_summary.csv", "games_summary.txt"):
        assert (out / name).is_file()
    txt = (out / "sessions.txt").read_text()
    assert "Jogo A" in txt and "01:00:00" in txt
    csv_text = (out / "games_summary.csv").read_text()
    assert "Jogo A" in csv_text and "3600" in csv_text


def test_default_export_dir(tmp_path):
    db = tmp_path / "database" / "x.db"
    assert default_export_dir(db) == tmp_path / "exports"
    flat = tmp_path / "x.db"
    assert default_export_dir(flat) == tmp_path / "exports"
