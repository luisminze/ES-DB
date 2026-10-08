"""Exportação de sessões para CSV/TXT (porta do ``export.sh`` do
GameSessionTracker para o software ES-DB).

Lê o banco de sessões em **somente leitura** e grava quatro arquivos em
``<pasta do ES-DB>/exports``: ``sessions.csv/txt`` e ``games_summary.csv/txt``.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path


def _fmt_duration(seconds: int) -> str:
    seconds = int(seconds or 0)
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"


def default_export_dir(db_path: str | Path) -> Path:
    db = Path(db_path).expanduser()
    if db.parent.name == "database":
        return db.parent.parent / "exports"
    return db.parent / "exports"


def export_sessions(db_path: str | Path,
                    out_dir: str | Path | None = None) -> Path:
    db = Path(db_path).expanduser()
    out = Path(out_dir).expanduser() if out_dir else default_export_dir(db)
    out.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        sessions = conn.execute(
            "SELECT sessions.id AS session_id, games.name AS game, "
            "games.platform AS platform, games.system AS system, games.rom AS rom, "
            "sessions.start_time, sessions.end_time, sessions.duration "
            "FROM sessions JOIN games ON games.id = sessions.game_id "
            "ORDER BY sessions.start_time").fetchall()
        summary = conn.execute(
            "SELECT games.name AS game, games.platform AS platform, "
            "COUNT(sessions.id) AS sessions, SUM(sessions.duration) AS total_seconds, "
            "MIN(sessions.start_time) AS first_session, "
            "MAX(sessions.end_time) AS last_session "
            "FROM sessions JOIN games ON games.id = sessions.game_id "
            "GROUP BY games.id ORDER BY SUM(sessions.duration) DESC").fetchall()
    finally:
        conn.close()

    # sessions.csv
    with (out / "sessions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["session_id", "game", "platform", "system", "rom",
                    "start_time", "end_time", "duration_seconds"])
        for r in sessions:
            w.writerow([r["session_id"], r["game"], r["platform"], r["system"],
                        r["rom"], r["start_time"], r["end_time"], r["duration"]])

    # sessions.txt
    with (out / "sessions.txt").open("w", encoding="utf-8") as f:
        f.write("ID | Jogo | Plataforma | Sistema | Início | Fim | Duração | ROM\n")
        f.write("-" * 90 + "\n")
        for r in sessions:
            f.write(" | ".join(str(x) for x in [
                r["session_id"], r["game"], r["platform"], r["system"],
                r["start_time"], r["end_time"],
                _fmt_duration(r["duration"]), r["rom"]]) + "\n")

    # games_summary.csv
    with (out / "games_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["game", "platform", "sessions", "total_seconds",
                    "first_session", "last_session"])
        for r in summary:
            w.writerow([r["game"], r["platform"], r["sessions"],
                        r["total_seconds"], r["first_session"], r["last_session"]])

    # games_summary.txt
    with (out / "games_summary.txt").open("w", encoding="utf-8") as f:
        f.write("Jogo | Plataforma | Sessões | Tempo total | Primeira | Última\n")
        f.write("-" * 90 + "\n")
        for r in summary:
            f.write(" | ".join(str(x) for x in [
                r["game"], r["platform"], r["sessions"],
                _fmt_duration(r["total_seconds"]),
                r["first_session"], r["last_session"]]) + "\n")
    return out
