"""Recursos empacotados do ES-DB (ícone do aplicativo etc.)."""

from __future__ import annotations

import sys
from pathlib import Path

_DIR = Path(__file__).resolve().parent

ICON_PATH = _DIR / "icon.png"


def icon_file() -> str | None:
    """Caminho do ícone do aplicativo, ou ``None`` se ausente.

    Funciona tanto em execução normal quanto empacotado (PyInstaller/AppImage),
    onde os dados ficam sob ``sys._MEIPASS``.
    """
    candidates = [ICON_PATH]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.insert(0, Path(meipass) / "esdb" / "resources" / "icon.png")
    for c in candidates:
        if c.is_file():
            return str(c)
    return None
