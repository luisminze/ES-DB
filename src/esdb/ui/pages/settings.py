"""Página Configurações — passo único do ES-DE + fonte + tema (MAIN.md RF-01)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (QComboBox, QFileDialog, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QVBoxLayout, QWidget)

from ...config import stats_home
from ...data.source_adapter import GameSessionTrackerSqliteAdapter
from ...esde.resolver import discover_session_databases, resolve_esde
from ...esde.writer import (create_database, install_scripts, remove_scripts,
                            scripts_installed)
from ..widgets import section_title
from .base import scroll_container


class SettingsPage(QWidget):
    def __init__(self, app) -> None:
        super().__init__()
        self._app = app
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._area, self._content, self._lay = scroll_container()
        outer.addWidget(self._area)

        self._lay.addWidget(section_title("Diretório do ES-DE"))
        self._lay.addWidget(QLabel(
            "Informe a pasta de configuração do ES-DE. O ES-DB descobre scripts, "
            "imagens, metadados e o banco de sessões automaticamente."))
        esde_row = QHBoxLayout()
        self._esde_edit = QLineEdit(app.config.esde_home)
        browse = QPushButton("Procurar…")
        browse.setObjectName("ChromeBtn")
        browse.clicked.connect(self._browse_esde)
        esde_row.addWidget(self._esde_edit, 1)
        esde_row.addWidget(browse)
        self._lay.addLayout(esde_row)
        self._status = QLabel()
        self._status.setObjectName("CardMeta")
        self._lay.addWidget(self._status)

        self._lay.addWidget(section_title("Banco de sessões"))
        db_row = QHBoxLayout()
        self._db_combo = QComboBox()
        self._db_combo.setEditable(True)
        db_browse = QPushButton("Procurar…")
        db_browse.setObjectName("ChromeBtn")
        db_browse.clicked.connect(self._browse_db)
        db_row.addWidget(self._db_combo, 1)
        db_row.addWidget(db_browse)
        self._lay.addLayout(db_row)
        self._db_status = QLabel()
        self._db_status.setObjectName("CardMeta")
        self._lay.addWidget(self._db_status)

        self._lay.addWidget(section_title("Gravação e scripts do ES-DE"))
        self._lay.addWidget(QLabel(
            "Crie um banco de sessões e instale os hooks game-start/game-end no "
            "ES-DE para começar a registrar partidas. Ative também no ES-DE: Menu "
            "→ Other Settings → Enable Custom Event Scripts."))
        create_row = QHBoxLayout()
        self._new_db_name = QLineEdit()
        self._new_db_name.setPlaceholderText("Nome do novo banco (ex.: Ricardo)")
        create_btn = QPushButton("Criar banco")
        create_btn.setObjectName("ChromeBtn")
        create_btn.clicked.connect(self._create_db)
        create_row.addWidget(self._new_db_name, 1)
        create_row.addWidget(create_btn)
        self._lay.addLayout(create_row)

        scripts_row = QHBoxLayout()
        install_btn = QPushButton("Instalar scripts (→ banco acima)")
        install_btn.setObjectName("ChromeBtn")
        install_btn.clicked.connect(self._install_scripts)
        remove_btn = QPushButton("Remover scripts do ES-DB")
        remove_btn.setObjectName("ChromeBtn")
        remove_btn.clicked.connect(self._remove_scripts)
        scripts_row.addWidget(install_btn)
        scripts_row.addWidget(remove_btn)
        scripts_row.addStretch()
        self._lay.addLayout(scripts_row)
        self._scripts_status = QLabel()
        self._scripts_status.setObjectName("CardMeta")
        self._lay.addWidget(self._scripts_status)

        self._lay.addWidget(section_title("Conquistas (emuladores)"))
        self._lay.addWidget(QLabel(
            "Aponte a pasta de troféus de cada emulador. Deixe em branco para "
            "detecção automática. Somente leitura — nada é modificado."))
        self._emu_edits: dict[str, QLineEdit] = {}
        for key, label, attr in (
            ("rpcs3", "RPCS3", "rpcs3_dir"),
            ("shadps4", "shadPS4", "shadps4_dir"),
            ("xenia", "Xenia", "xenia_dir"),
        ):
            row = QHBoxLayout()
            tag = QLabel(label)
            tag.setFixedWidth(80)
            edit = QLineEdit(getattr(app.config, attr))
            browse = QPushButton("Procurar…")
            browse.setObjectName("ChromeBtn")
            browse.clicked.connect(lambda _=False, e=edit: self._browse_dir(e))
            row.addWidget(tag)
            row.addWidget(edit, 1)
            row.addWidget(browse)
            self._lay.addLayout(row)
            self._emu_edits[attr] = edit

        self._lay.addWidget(section_title("Aparência"))
        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Tema:"))
        self._theme = QComboBox()
        self._theme.addItems(["escuro", "claro"])
        self._theme.setCurrentText("claro" if app.config.theme == "light" else "escuro")
        theme_row.addWidget(self._theme)
        theme_row.addStretch()
        self._lay.addLayout(theme_row)

        save = QPushButton("Salvar e recarregar")
        save.setObjectName("ChromeBtn")
        save.clicked.connect(self._save)
        integrity = QPushButton("Ver integridade dos dados")
        integrity.setObjectName("ChromeBtn")
        integrity.clicked.connect(lambda: self._app.navigate("integrity"))
        save_row = QHBoxLayout()
        save_row.addWidget(save)
        save_row.addWidget(integrity)
        save_row.addStretch()
        self._lay.addLayout(save_row)
        self._lay.addStretch()

    def _browse_esde(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Diretório do ES-DE",
                                                self._esde_edit.text() or str(Path.home()))
        if path:
            self._esde_edit.setText(path)
            self.update_view()

    def _create_db(self) -> None:
        name = self._new_db_name.text().strip()
        if not name:
            self._scripts_status.setText("✕ Informe um nome para o banco.")
            return
        safe = "".join(c for c in name if c not in "/\\")
        target = stats_home() / "DATABASE" / f"{safe}.db"
        try:
            create_database(target)
        except FileExistsError:
            self._scripts_status.setText(f"✕ Já existe: {target}")
            return
        except OSError as exc:
            self._scripts_status.setText(f"✕ Erro: {exc}")
            return
        self._db_combo.setCurrentText(str(target))
        self._new_db_name.clear()
        self.update_view()
        self._scripts_status.setText(f"✓ Banco criado: {target}")

    def _install_scripts(self) -> None:
        db = self._db_combo.currentText().strip()
        scripts = resolve_esde(self._esde_edit.text() or None).scripts
        if not db:
            self._scripts_status.setText("✕ Selecione um banco de sessões.")
            return
        try:
            written = install_scripts(scripts, db)
        except OSError as exc:
            self._scripts_status.setText(f"✕ Erro ao instalar: {exc}")
            return
        self._scripts_status.setText(
            f"✓ {len(written)} scripts instalados em {scripts} → {db}")

    def _remove_scripts(self) -> None:
        scripts = resolve_esde(self._esde_edit.text() or None).scripts
        removed = remove_scripts(scripts)
        self._scripts_status.setText(
            f"✓ {len(removed)} script(s) do ES-DB removidos."
            if removed else "Nenhum script do ES-DB encontrado.")

    def _browse_dir(self, edit: QLineEdit) -> None:
        path = QFileDialog.getExistingDirectory(self, "Pasta do emulador",
                                                edit.text() or str(Path.home()))
        if path:
            edit.setText(path)

    def _browse_db(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Banco de sessões",
                                              str(Path.home()), "SQLite (*.db *.sqlite)")
        if path:
            self._db_combo.setCurrentText(path)
            self._probe_db(path)

    def _probe_db(self, path: str) -> None:
        probe = GameSessionTrackerSqliteAdapter(path).validate()
        self._db_status.setText(("✓ " if probe.ok else "✕ ") + probe.message)

    def update_view(self) -> None:
        layout = resolve_esde(self._esde_edit.text() or None)
        found = layout.found()
        marks = "   ".join(
            f"{'✓' if ok else '✕'} {name}" for name, ok in found.items())
        self._status.setText(
            f"{marks}" if layout.exists() else "Diretório do ES-DE não encontrado.")
        current = self._db_combo.currentText()
        self._db_combo.blockSignals(True)
        self._db_combo.clear()
        candidates = [str(p) for p in discover_session_databases()]
        self._db_combo.addItems(candidates)
        chosen = current or self._app.config.session_db
        if chosen:
            self._db_combo.setCurrentText(chosen)
        self._db_combo.blockSignals(False)
        if self._db_combo.currentText():
            self._probe_db(self._db_combo.currentText())
        installed = scripts_installed(layout.scripts)
        self._scripts_status.setText(
            "✓ Scripts do ES-DB instalados." if installed
            else "Scripts do ES-DB não instalados.")

    def _save(self) -> None:
        cfg = self._app.config
        cfg.esde_home = self._esde_edit.text().strip()
        cfg.session_db = self._db_combo.currentText().strip()
        cfg.theme = "light" if self._theme.currentText() == "claro" else "dark"
        for attr, edit in self._emu_edits.items():
            setattr(cfg, attr, edit.text().strip())
        self._app.reconfigure(cfg)
