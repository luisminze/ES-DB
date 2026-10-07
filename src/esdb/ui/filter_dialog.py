"""Painel de filtros da Biblioteca — menu suspenso renovado (FILTROS.md, Update1).

É um popup ancorado ao ícone de Filtros da barra superior, em colunas
(plataformas, gênero, desenvolvedora, opções) com predefinições salvas.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFrame, QGridLayout,
                               QHBoxLayout, QInputDialog, QLabel, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)


def _section(text: str, accent: str) -> QWidget:
    host = QWidget()
    h = QHBoxLayout(host)
    h.setContentsMargins(0, 2, 0, 2)
    h.setSpacing(8)
    bar = QFrame()
    bar.setFixedSize(3, 13)
    bar.setStyleSheet(f"background: {accent}; border-radius: 2px;")
    lab = QLabel(text.upper())
    f = QFont(lab.font())
    f.setPointSize(9)
    f.setBold(True)
    try:
        f.setLetterSpacing(QFont.AbsoluteSpacing, 1.5)
    except Exception:
        pass
    lab.setFont(f)
    lab.setStyleSheet(f"color: {accent};")
    h.addWidget(bar)
    h.addWidget(lab)
    h.addStretch()
    return host


def _checklist(values: list[str], selected: set[str]) -> tuple[QWidget, list[QCheckBox]]:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    area.setMaximumHeight(170)
    host = QWidget()
    host.setObjectName("ScrollBody")
    lay = QVBoxLayout(host)
    lay.setContentsMargins(2, 2, 2, 2)
    lay.setSpacing(2)
    boxes: list[QCheckBox] = []
    for v in values:
        cb = QCheckBox(v)
        cb.setChecked(v in selected)
        boxes.append(cb)
        lay.addWidget(cb)
    lay.addStretch()
    area.setWidget(host)
    return area, boxes


class FilterPanel(QFrame):
    def __init__(self, app) -> None:
        super().__init__(app.window, Qt.Popup)
        self.setObjectName("FilterPanel")
        self.setStyleSheet(app.window.styleSheet())
        self._app = app
        self._accent = "#EB5E54"
        lib = app.library

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Filtros")
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(QLabel("Predefinição:"))
        self._preset_combo = QComboBox()
        self._preset_combo.setMinimumWidth(150)
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
        for wdg in (self._preset_combo, apply_preset, save_preset, del_preset):
            header.addWidget(wdg)
        root.addLayout(header)

        columns = QHBoxLayout()
        columns.setSpacing(22)

        # Coluna 1 — plataformas
        col1 = QVBoxLayout()
        col1.addWidget(_section("Plataformas", self._accent))
        area, self._plat_boxes = _checklist(lib.platforms if lib else [],
                                            app.filters["platforms"])
        col1.addWidget(area)
        col1.addStretch()
        c1 = QWidget(); c1.setLayout(col1)
        columns.addWidget(c1, 1)

        # Coluna 2 — gênero + desenvolvedora (metadados do ES-DE)
        self._genre_boxes: list[QCheckBox] = []
        self._dev_boxes: list[QCheckBox] = []
        col2 = QVBoxLayout()
        if lib and lib.has_metadata():
            genres = lib.genres()
            if genres:
                col2.addWidget(_section("Gênero (ES-DE)", self._accent))
                ga, self._genre_boxes = _checklist(genres, app.filters["genres"])
                col2.addWidget(ga)
            devs = lib.developers()
            if devs:
                col2.addWidget(_section("Desenvolvedora (ES-DE)", self._accent))
                da, self._dev_boxes = _checklist(devs, app.filters["developers"])
                col2.addWidget(da)
            col2.addStretch()
        else:
            col2.addWidget(QLabel("Sem metadados do ES-DE para gênero/desenvolvedora."))
            col2.addStretch()
        c2 = QWidget(); c2.setLayout(col2)
        columns.addWidget(c2, 1)

        # Coluna 3 — opções
        col3 = QVBoxLayout()
        col3.addWidget(_section("Opções", self._accent))
        opts = app.filters["options"]
        self._opt_recent = QCheckBox("Apenas jogados recentemente (7 dias)")
        self._opt_recent.setChecked(opts.get("recent7", False))
        self._opt_cover = QCheckBox("Apenas com capa")
        self._opt_cover.setChecked(opts.get("only_cover", False))
        self._opt_shots = QCheckBox("Apenas com screenshots")
        self._opt_shots.setChecked(opts.get("only_screenshots", False))
        for cb in (self._opt_recent, self._opt_cover, self._opt_shots):
            col3.addWidget(cb)
        col3.addStretch()
        c3 = QWidget(); c3.setLayout(col3)
        columns.addWidget(c3, 1)
        root.addLayout(columns)

        footer = QHBoxLayout()
        clear = QPushButton("Limpar")
        clear.setObjectName("ChromeBtn")
        clear.clicked.connect(self._clear)
        apply_btn = QPushButton("Aplicar filtros")
        apply_btn.setObjectName("ChromeBtn")
        apply_btn.clicked.connect(self._apply)
        footer.addWidget(clear)
        footer.addStretch()
        footer.addWidget(apply_btn)
        root.addLayout(footer)
        self.setFixedWidth(760)

    # ----------------------------------------------------------- posição
    def open_under(self, anchor) -> None:
        self.adjustSize()
        gp = anchor.mapToGlobal(QPoint(0, anchor.height() + 6))
        screen = anchor.screen().availableGeometry()
        x = min(gp.x(), screen.right() - self.width() - 8)
        x = max(screen.left() + 8, x - self.width() + anchor.width())
        self.move(x, gp.y())
        self.show()

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
        data = self._app.library.store.get_presets().get(self._preset_combo.currentText())
        if not data:
            return
        plats, genres, devs = (set(data.get("platforms", [])),
                               set(data.get("genres", [])),
                               set(data.get("developers", [])))
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

    def _clear(self) -> None:
        for cb in (self._plat_boxes + self._genre_boxes + self._dev_boxes +
                   [self._opt_recent, self._opt_cover, self._opt_shots]):
            cb.setChecked(False)

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
        self.close()
