"""Painel de filtros da Biblioteca (FILTROS.md)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout,
                               QInputDialog, QLabel, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

from .widgets import section_title


class FilterDialog(QDialog):
    def __init__(self, app) -> None:
        super().__init__(app.window)
        self.setWindowTitle("Filtros")
        self.resize(360, 620)
        self.setStyleSheet(app.window.styleSheet())
        self._app = app
        lib = app.library

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(10)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Predefinição:"))
        self._preset_combo = QComboBox()
        self._reload_presets()
        apply_preset = QPushButton("Aplicar")
        apply_preset.setObjectName("ChromeBtn")
        apply_preset.clicked.connect(self._apply_preset)
        save_preset = QPushButton("Salvar")
        save_preset.setObjectName("ChromeBtn")
        save_preset.clicked.connect(self._save_preset)
        del_preset = QPushButton("Excluir")
        del_preset.setObjectName("ChromeBtn")
        del_preset.clicked.connect(self._delete_preset)
        preset_row.addWidget(self._preset_combo, 1)
        preset_row.addWidget(apply_preset)
        preset_row.addWidget(save_preset)
        preset_row.addWidget(del_preset)
        root.addLayout(preset_row)

        area = QScrollArea()
        area.setWidgetResizable(True)
        host = QWidget()
        lay = QVBoxLayout(host)
        area.setWidget(host)
        root.addWidget(area, 1)

        self._plat_boxes: list[QCheckBox] = []
        self._genre_boxes: list[QCheckBox] = []
        self._dev_boxes: list[QCheckBox] = []

        lay.addWidget(section_title("Plataformas"))
        for plat in (lib.platforms if lib else []):
            cb = QCheckBox(plat)
            cb.setChecked(plat in app.filters["platforms"])
            self._plat_boxes.append(cb)
            lay.addWidget(cb)

        if lib and lib.has_metadata():
            genres = lib.genres()
            if genres:
                lay.addWidget(section_title("Gênero (ES-DE)"))
                for gnr in genres:
                    cb = QCheckBox(gnr)
                    cb.setChecked(gnr in app.filters["genres"])
                    self._genre_boxes.append(cb)
                    lay.addWidget(cb)
            devs = lib.developers()
            if devs:
                lay.addWidget(section_title("Desenvolvedora (ES-DE)"))
                for dev in devs:
                    cb = QCheckBox(dev)
                    cb.setChecked(dev in app.filters["developers"])
                    self._dev_boxes.append(cb)
                    lay.addWidget(cb)

        lay.addWidget(section_title("Opções"))
        self._opt_recent = QCheckBox("Apenas jogados recentemente (7 dias)")
        self._opt_recent.setChecked(app.filters["options"].get("recent7", False))
        self._opt_cover = QCheckBox("Apenas com capa")
        self._opt_cover.setChecked(app.filters["options"].get("only_cover", False))
        self._opt_shots = QCheckBox("Apenas com screenshots")
        self._opt_shots.setChecked(app.filters["options"].get("only_screenshots", False))
        for cb in (self._opt_recent, self._opt_cover, self._opt_shots):
            lay.addWidget(cb)
        lay.addStretch()

        buttons = QHBoxLayout()
        clear = QPushButton("Limpar")
        clear.setObjectName("ChromeBtn")
        clear.clicked.connect(self._clear)
        apply_btn = QPushButton("Aplicar")
        apply_btn.setObjectName("ChromeBtn")
        apply_btn.clicked.connect(self._apply)
        buttons.addWidget(clear)
        buttons.addStretch()
        buttons.addWidget(apply_btn)
        root.addLayout(buttons)

    def _clear(self) -> None:
        for cb in (self._plat_boxes + self._genre_boxes + self._dev_boxes +
                   [self._opt_recent, self._opt_cover, self._opt_shots]):
            cb.setChecked(False)

    # ----------------------------------------------------------- presets
    def _reload_presets(self) -> None:
        self._preset_combo.clear()
        self._preset_combo.addItem("—")
        for name in sorted(self._app.library.store.get_presets()):
            self._preset_combo.addItem(name)

    def _current_filter_data(self) -> dict:
        return {
            "platforms": [cb.text() for cb in self._plat_boxes if cb.isChecked()],
            "genres": [cb.text() for cb in self._genre_boxes if cb.isChecked()],
            "developers": [cb.text() for cb in self._dev_boxes if cb.isChecked()],
            "options": {
                "recent7": self._opt_recent.isChecked(),
                "only_cover": self._opt_cover.isChecked(),
                "only_screenshots": self._opt_shots.isChecked(),
            },
        }

    def _apply_preset(self) -> None:
        name = self._preset_combo.currentText()
        data = self._app.library.store.get_presets().get(name)
        if not data:
            return
        plats = set(data.get("platforms", []))
        genres = set(data.get("genres", []))
        devs = set(data.get("developers", []))
        opts = data.get("options", {})
        for cb in self._plat_boxes:
            cb.setChecked(cb.text() in plats)
        for cb in self._genre_boxes:
            cb.setChecked(cb.text() in genres)
        for cb in self._dev_boxes:
            cb.setChecked(cb.text() in devs)
        self._opt_recent.setChecked(opts.get("recent7", False))
        self._opt_cover.setChecked(opts.get("only_cover", False))
        self._opt_shots.setChecked(opts.get("only_screenshots", False))

    def _save_preset(self) -> None:
        name, ok = QInputDialog.getText(self, "Salvar predefinição",
                                        "Nome da predefinição:")
        if ok and name.strip():
            self._app.library.store.save_preset(name.strip(),
                                                self._current_filter_data())
            self._reload_presets()
            self._preset_combo.setCurrentText(name.strip())

    def _delete_preset(self) -> None:
        name = self._preset_combo.currentText()
        if name and name != "—":
            self._app.library.store.delete_preset(name)
            self._reload_presets()

    def _apply(self) -> None:
        f = self._app.filters
        f["platforms"] = {cb.text() for cb in self._plat_boxes if cb.isChecked()}
        f["genres"] = {cb.text() for cb in self._genre_boxes if cb.isChecked()}
        f["developers"] = {cb.text() for cb in self._dev_boxes if cb.isChecked()}
        f["options"] = {
            "recent7": self._opt_recent.isChecked(),
            "only_cover": self._opt_cover.isChecked(),
            "only_screenshots": self._opt_shots.isChecked(),
        }
        self._app.navigate("library")
        self._app.refresh_pages()
        self.accept()
