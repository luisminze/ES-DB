"""Bootstrap da aplicação Qt."""

from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .config import load_config
from .resources import icon_file
from .ui.main_window import MainWindow


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("ES-DB")
    app.setApplicationDisplayName("ES-DB")
    app.setOrganizationName("ES-DB")
    app.setDesktopFileName("es-db")
    icon = icon_file()
    if icon:
        app.setWindowIcon(QIcon(icon))
    config = load_config()
    window = MainWindow(config)
    window.show()
    return app.exec()
