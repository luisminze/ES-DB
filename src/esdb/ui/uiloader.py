"""Carregador de telas .ui (Qt Designer) em tempo de execução, via QUiLoader.

Permite desenhar formulários estáticos no **Qt Designer** (``designer``), salvar
como ``.ui`` em ``ui/designer/`` e carregá-los aqui, mantendo a lógica em Python.
Funciona tanto a partir do código-fonte quanto do AppImage (PyInstaller).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader


def designer_dir() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        frozen = Path(meipass) / "esdb" / "ui" / "designer"
        if frozen.is_dir():
            return frozen
    return Path(__file__).resolve().parent / "designer"


def load_ui(name: str, parent=None):
    """Carrega ``ui/designer/<name>`` e retorna o widget raiz."""
    path = designer_dir() / name
    f = QFile(str(path))
    if not f.open(QFile.ReadOnly):
        raise FileNotFoundError(f"Arquivo .ui não encontrado: {path}")
    try:
        widget = QUiLoader().load(f, parent)
    finally:
        f.close()
    if widget is None:
        raise RuntimeError(f"Falha ao carregar o .ui: {path}")
    return widget
