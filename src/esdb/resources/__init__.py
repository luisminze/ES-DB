"""Recursos empacotados do ES-DB (ícone do aplicativo etc.)."""

from __future__ import annotations

from pathlib import Path

_DIR = Path(__file__).resolve().parent

ICON_PATH = _DIR / "icon.png"


def icon_file() -> str | None:
    """Caminho do ícone do aplicativo, ou ``None`` se ausente."""
    return str(ICON_PATH) if ICON_PATH.is_file() else None
