"""Editor de tema ao vivo: ajusta as cores da paleta e reaplica o QSS na hora."""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QColorDialog, QDialogButtonBox, QGridLayout,
                               QHBoxLayout, QLabel, QPushButton, QScrollArea,
                               QDialog, QVBoxLayout, QWidget)

from .. import theme as T


class ThemeEditorDialog(QDialog):
    def __init__(self, app) -> None:
        super().__init__(app.window)
        self._app = app
        self._theme_key = T.resolve_theme(app.config.theme)  # 'dark' | 'light'
        self._working = dict(T.palette(app.config.theme))
        self.setObjectName("Panel")
        self.setStyleSheet(app.window.styleSheet())
        self.setWindowTitle(f"Editar cores — tema {self._theme_key}")
        self.resize(460, 620)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(10)
        head = QLabel(f"Tema “{self._theme_key}”. Clique numa cor para trocar — "
                      "a interface atualiza na hora. Salvar grava em theme.json.")
        head.setObjectName("CardMeta")
        head.setWordWrap(True)
        root.addWidget(head)

        area = QScrollArea()
        area.setWidgetResizable(True)
        host = QWidget()
        host.setObjectName("ScrollBody")
        grid = QGridLayout(host)
        grid.setContentsMargins(2, 2, 8, 8)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        self._swatches: dict[str, QPushButton] = {}
        for i, (key, label) in enumerate(T.EDITABLE.items()):
            name = QLabel(label)
            swatch = QPushButton(self._working.get(key, ""))
            swatch.setMinimumWidth(130)
            swatch.clicked.connect(lambda _=False, k=key: self._pick(k))
            self._swatches[key] = swatch
            self._paint(key)
            grid.addWidget(name, i, 0)
            grid.addWidget(swatch, i, 1)
        area.setWidget(host)
        root.addWidget(area, 1)

        buttons = QDialogButtonBox()
        save = buttons.addButton("Salvar", QDialogButtonBox.AcceptRole)
        reset = buttons.addButton("Restaurar padrão", QDialogButtonBox.ResetRole)
        close = buttons.addButton("Fechar", QDialogButtonBox.RejectRole)
        save.clicked.connect(self._save)
        reset.clicked.connect(self._reset)
        close.clicked.connect(self._cancel)
        root.addWidget(buttons)

    def _paint(self, key: str) -> None:
        color = self._working.get(key, "#000000")
        sw = self._swatches[key]
        sw.setText(color)
        fg = "#000000" if QColor(color).lightnessF() > 0.5 else "#FFFFFF"
        sw.setStyleSheet(
            f"background: {color}; color: {fg}; border: 1px solid #888; "
            "border-radius: 6px; padding: 6px 10px;")

    def _pick(self, key: str) -> None:
        initial = QColor(self._working.get(key, "#000000"))
        chosen = QColorDialog.getColor(initial, self, f"Cor: {T.EDITABLE[key]}")
        if chosen.isValid():
            self._working[key] = chosen.name()
            self._paint(key)
            self._preview()

    def _preview(self) -> None:
        T.set_active(self._working)
        self._app.window.setStyleSheet(T.build_qss(self._working))

    def _save(self) -> None:
        T.save_overrides(self._theme_key, self._working)
        self._app._apply_theme()
        if self._app._current:
            self._app.pages[self._app._current].update_view()
        self.accept()

    def _reset(self) -> None:
        T.reset_overrides(self._theme_key)
        self._working = dict(T.base_palette(self._app.config.theme))
        for key in T.EDITABLE:
            self._paint(key)
        self._preview()

    def _cancel(self) -> None:
        self._app._apply_theme()  # descarta o preview, volta ao salvo
        self.reject()
