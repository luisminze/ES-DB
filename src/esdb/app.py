"""Bootstrap da aplicação Qt."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .config import load_config
from .ui.main_window import MainWindow


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("ES-DB")
    app.setOrganizationName("ES-DB")
    config = load_config()
    window = MainWindow(config)
    window.show()
    return app.exec()
