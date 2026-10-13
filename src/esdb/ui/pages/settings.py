"""Página Configurações — Tema, Banco de dados e Integrações (ES-DE/Lutris/Heroic/Conquistas)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFrame,
                               QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QVBoxLayout, QWidget)

from ...config import stats_home
from ...data.source_adapter import GameSessionTrackerSqliteAdapter
from ...esde.heroic import default_heroic_dir
from ...esde.resolver import discover_session_databases, resolve_esde
from ...esde.writer import (create_database, heroic_scripts_installed,
                            install_heroic_scripts, install_lutris_scripts,
                            install_scripts, lutris_scripts_installed,
                            remove_heroic_scripts, remove_lutris_scripts,
                            remove_scripts, scripts_installed)
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

        # ----------------------------------------------------------- Tema
        self._lay.addWidget(section_title("Tema"))
        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Tema:"))
        self._theme = QComboBox()
        for label, value in (("Claro", "light"), ("Escuro", "dark"),
                             ("Sistema", "system")):
            self._theme.addItem(label, value)
        idx = self._theme.findData(app.config.theme)
        self._theme.setCurrentIndex(idx if idx >= 0 else 1)
        hint_sys = QLabel("(Sistema segue o tema do seu SO automaticamente)")
        hint_sys.setObjectName("CardMeta")
        theme_row.addWidget(self._theme)
        theme_row.addWidget(hint_sys)
        theme_row.addStretch()
        self._lay.addLayout(theme_row)

        # --------------------------------------------------- Banco de dados
        self._lay.addWidget(section_title("Banco de dados"))
        self._lay.addWidget(QLabel(
            "Banco único de sessões — todas as integrações gravam nele."))
        db_row = QHBoxLayout()
        self._db_combo = QComboBox()
        self._db_combo.setEditable(True)
        db_browse = QPushButton("Procurar…")
        db_browse.setObjectName("ChromeBtn")
        db_browse.clicked.connect(self._browse_db)
        db_row.addWidget(self._db_combo, 1)
        db_row.addWidget(db_browse)
        self._lay.addLayout(db_row)
        create_row = QHBoxLayout()
        self._new_db_name = QLineEdit()
        self._new_db_name.setPlaceholderText("Nome do novo banco (ex.: Ricardo)")
        create_btn = QPushButton("Criar banco")
        create_btn.setObjectName("ChromeBtn")
        create_btn.clicked.connect(self._create_db)
        create_row.addWidget(self._new_db_name, 1)
        create_row.addWidget(create_btn)
        self._lay.addLayout(create_row)
        self._db_status = QLabel()
        self._db_status.setObjectName("CardMeta")
        self._lay.addWidget(self._db_status)

        # ----------------------------------------------------- Integrações
        self._lay.addWidget(section_title("Integrações"))

        # -- ES-DE --------------------------------------------------------
        self._esde_box, esde_lay = self._integration(
            "ES-DE", app.config.esde_enabled)
        esde_lay.addWidget(QLabel(
            "Pasta de configuração do ES-DE. Descobre scripts, imagens, "
            "metadados e o banco de sessões automaticamente."))
        esde_row = QHBoxLayout()
        self._esde_edit = QLineEdit(app.config.esde_home)
        browse = QPushButton("Procurar…")
        browse.setObjectName("ChromeBtn")
        browse.clicked.connect(self._browse_esde)
        esde_row.addWidget(self._esde_edit, 1)
        esde_row.addWidget(browse)
        esde_lay.addLayout(esde_row)
        self._status = QLabel()
        self._status.setObjectName("CardMeta")
        esde_lay.addWidget(self._status)
        esde_btns = QHBoxLayout()
        for text, slot in (("Instalar scripts", self._install_scripts),
                           ("Remover scripts", self._remove_scripts),
                           ("Importar metadados", self._import_metadata),
                           ("Exportar sessões (CSV/TXT)", self._export_sessions)):
            b = QPushButton(text)
            b.setObjectName("ChromeBtn")
            b.clicked.connect(slot)
            esde_btns.addWidget(b)
        esde_btns.addStretch()
        esde_lay.addLayout(esde_btns)
        self._scripts_status = QLabel()
        self._scripts_status.setObjectName("CardMeta")
        esde_lay.addWidget(self._scripts_status)

        # -- Lutris -------------------------------------------------------
        self._lutris_box, lutris_lay = self._integration(
            "Lutris", app.config.lutris_enabled)
        lutris_lay.addWidget(QLabel(
            "Gere os scripts e, nas opções de Sistema do Lutris (globais ou por "
            "jogo), aponte o “Comando pré-lançamento” para lutris-game-start.sh "
            "e o “Comando pós-saída” para lutris-game-end.sh."))
        lrow = QHBoxLayout()
        for text, slot in (("Instalar scripts", self._install_lutris),
                           ("Remover scripts", self._remove_lutris)):
            b = QPushButton(text)
            b.setObjectName("ChromeBtn")
            b.clicked.connect(slot)
            lrow.addWidget(b)
        lrow.addStretch()
        lutris_lay.addLayout(lrow)
        self._lutris_status = QLabel()
        self._lutris_status.setObjectName("CardMeta")
        self._lutris_status.setWordWrap(True)
        lutris_lay.addWidget(self._lutris_status)

        # -- Heroic -------------------------------------------------------
        self._heroic_box, heroic_lay = self._integration(
            "Heroic Games Launcher", app.config.heroic_enabled)
        heroic_lay.addWidget(QLabel(
            "Gere o wrapper e, no Heroic (Configurações → Avançado → “Wrapper”, "
            "global ou por jogo), aponte para heroic-wrapper.sh. O wrapper roda "
            "no ambiente do jogo e o identifica de forma confiável (inclusive "
            "jogos sideload). Não use os scripts “antes/depois” para isto."))
        hdir_row = QHBoxLayout()
        hdir_row.addWidget(QLabel("Config do Heroic:"))
        self._heroic_edit = QLineEdit(
            app.config.heroic_dir or str(default_heroic_dir() or ""))
        hbrowse = QPushButton("Procurar…")
        hbrowse.setObjectName("ChromeBtn")
        hbrowse.clicked.connect(lambda: self._browse_dir(self._heroic_edit))
        hdir_row.addWidget(self._heroic_edit, 1)
        hdir_row.addWidget(hbrowse)
        heroic_lay.addLayout(hdir_row)
        hrow = QHBoxLayout()
        for text, slot in (("Instalar scripts", self._install_heroic),
                           ("Remover scripts", self._remove_heroic)):
            b = QPushButton(text)
            b.setObjectName("ChromeBtn")
            b.clicked.connect(slot)
            hrow.addWidget(b)
        hrow.addStretch()
        heroic_lay.addLayout(hrow)
        self._heroic_status = QLabel()
        self._heroic_status.setObjectName("CardMeta")
        self._heroic_status.setWordWrap(True)
        heroic_lay.addWidget(self._heroic_status)

        # -- Conquistas ---------------------------------------------------
        self._ach_box, ach_lay = self._integration(
            "Conquistas", app.config.achievements_enabled,
            on_toggle=self._on_ach_toggled)
        ach_lay.addWidget(QLabel(
            "Troféus de RPCS3, Xenia e shadPS4. Aponte a pasta de troféus de cada "
            "emulador (vazio = detecção automática). Somente leitura. Ao desativar, "
            "a aba Conquistas é ocultada e o app reinicia."))
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
            b = QPushButton("Procurar…")
            b.setObjectName("ChromeBtn")
            b.clicked.connect(lambda _=False, e=edit: self._browse_dir(e))
            row.addWidget(tag)
            row.addWidget(edit, 1)
            row.addWidget(b)
            ach_lay.addLayout(row)
            self._emu_edits[attr] = edit

        # ----------------------------------------------------------- Dados
        self._lay.addWidget(section_title("Dados"))
        self._lay.addWidget(QLabel(
            "Apaga permanentemente as sessões gravadas no banco selecionado. "
            "Para limpar apenas um jogo, use “Limpar dados” na tela do jogo."))
        data_row = QHBoxLayout()
        clear_all = QPushButton("Limpar dados de TODOS os jogos")
        clear_all.setObjectName("ChromeBtn")
        clear_all.clicked.connect(self._clear_all_data)
        data_row.addWidget(clear_all)
        data_row.addStretch()
        self._lay.addLayout(data_row)
        self._data_status = QLabel()
        self._data_status.setObjectName("CardMeta")
        self._lay.addWidget(self._data_status)

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

    # ------------------------------------------------------------- helpers
    def _integration(self, title: str, enabled: bool, on_toggle=None):
        """Cabeçalho com checkbox + caixa recolhível. Retorna (checkbox, layout)."""
        chk = QCheckBox(title)
        chk.setChecked(enabled)
        chk.setStyleSheet("font-weight: 700; font-size: 15px;")
        self._lay.addWidget(chk)
        box = QFrame()
        box.setObjectName("Card")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)
        box.setVisible(enabled)
        self._lay.addWidget(box)

        def _vis(checked, b=box, extra=on_toggle):
            b.setVisible(checked)
            if extra:
                extra(checked)
        chk.toggled.connect(_vis)
        chk._box = box  # type: ignore[attr-defined]
        return chk, lay

    def _on_ach_toggled(self, checked: bool) -> None:
        pass

    # ------------------------------------------------------------- actions
    def _browse_esde(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Diretório do ES-DE",
                                                self._esde_edit.text() or str(Path.home()))
        if path:
            self._esde_edit.setText(path)
            self.update_view()

    def _import_metadata(self) -> None:
        self._app.reload_library()
        self._app.refresh_data()
        self._scripts_status.setText("✓ Metadados do ES-DE reimportados.")

    def _create_db(self) -> None:
        name = self._new_db_name.text().strip()
        if not name:
            self._db_status.setText("✕ Informe um nome para o banco.")
            return
        safe = "".join(c for c in name if c not in "/\\")
        target = stats_home() / "database" / f"{safe}.db"
        try:
            create_database(target)
        except FileExistsError:
            self._db_status.setText(f"✕ Já existe: {target}")
            return
        except OSError as exc:
            self._db_status.setText(f"✕ Erro: {exc}")
            return
        self._db_combo.setCurrentText(str(target))
        self._new_db_name.clear()
        self.update_view()
        self._db_status.setText(f"✓ Banco criado: {target}")

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

    def _export_sessions(self) -> None:
        from ...esde.export import export_sessions
        db = self._db_combo.currentText().strip()
        if not db:
            self._scripts_status.setText("✕ Selecione um banco de sessões.")
            return
        try:
            out = export_sessions(db)
        except Exception as exc:  # noqa: BLE001
            self._scripts_status.setText(f"✕ Falha ao exportar: {exc}")
            return
        self._scripts_status.setText(f"✓ Sessões exportadas para {out}")

    def _remove_scripts(self) -> None:
        scripts = resolve_esde(self._esde_edit.text() or None).scripts
        removed = remove_scripts(scripts)
        self._scripts_status.setText(
            f"✓ {len(removed)} script(s) do ES-DE removidos."
            if removed else "Nenhum script do ES-DE encontrado.")

    def _clear_all_data(self) -> None:
        lib = self._app.library
        if lib is None:
            self._data_status.setText("✕ Nenhum banco carregado.")
            return
        n = len(lib.games)
        resp = QMessageBox.warning(
            self, "Limpar TODOS os dados",
            f"Apagar PERMANENTEMENTE as sessões de todos os {n} jogos do banco\n"
            f"{lib.session_db}?\n\nEsta ação não pode ser desfeita.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if resp != QMessageBox.Yes:
            return
        lib.clear_all()
        self._app.refresh_pages()
        self._data_status.setText("✓ Todos os dados de jogos foram apagados.")

    # --------------------------------------------------------- Lutris/Heroic
    def _lutris_dir(self):
        return stats_home() / "lutris"

    def _heroic_scripts_dir(self):
        return stats_home() / "heroic"

    def _install_lutris(self) -> None:
        db = self._db_combo.currentText().strip()
        if not db:
            self._lutris_status.setText("✕ Selecione um banco de sessões.")
            return
        try:
            written = install_lutris_scripts(self._lutris_dir(), db)
        except OSError as exc:
            self._lutris_status.setText(f"✕ Erro ao gerar: {exc}")
            return
        paths = "\n".join(f"• {p}" for p in written)
        self._lutris_status.setText(
            f"✓ Scripts do Lutris gerados → banco {db}\n{paths}")

    def _remove_lutris(self) -> None:
        removed = remove_lutris_scripts(self._lutris_dir())
        self._lutris_status.setText(
            f"✓ {len(removed)} script(s) do Lutris removidos."
            if removed else "Nenhum script do Lutris encontrado.")

    def _install_heroic(self) -> None:
        db = self._db_combo.currentText().strip()
        if not db:
            self._heroic_status.setText("✕ Selecione um banco de sessões.")
            return
        try:
            written = install_heroic_scripts(self._heroic_scripts_dir(), db)
        except OSError as exc:
            self._heroic_status.setText(f"✕ Erro ao gerar: {exc}")
            return
        paths = "\n".join(f"• {p}" for p in written)
        self._heroic_status.setText(
            f"✓ Scripts do Heroic gerados → banco {db}\n{paths}")

    def _remove_heroic(self) -> None:
        removed = remove_heroic_scripts(self._heroic_scripts_dir())
        self._heroic_status.setText(
            f"✓ {len(removed)} script(s) do Heroic removidos."
            if removed else "Nenhum script do Heroic encontrado.")

    def _browse_dir(self, edit: QLineEdit) -> None:
        path = QFileDialog.getExistingDirectory(self, "Selecionar pasta",
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
        if not self._scripts_status.text():
            self._scripts_status.setText(
                "✓ Scripts do ES-DE instalados." if installed
                else "Scripts do ES-DE não instalados.")
        if not self._lutris_status.text():
            self._lutris_status.setText(
                f"✓ Scripts do Lutris gerados em {self._lutris_dir()}."
                if lutris_scripts_installed(self._lutris_dir())
                else "Scripts do Lutris não gerados.")
        if not self._heroic_status.text():
            self._heroic_status.setText(
                f"✓ Scripts do Heroic gerados em {self._heroic_scripts_dir()}."
                if heroic_scripts_installed(self._heroic_scripts_dir())
                else "Scripts do Heroic não gerados.")

    def _save(self) -> None:
        from dataclasses import replace
        changes = {
            "esde_home": self._esde_edit.text().strip(),
            "session_db": self._db_combo.currentText().strip(),
            "theme": self._theme.currentData() or "dark",
            "achievements_enabled": self._ach_box.isChecked(),
            "esde_enabled": self._esde_box.isChecked(),
            "lutris_enabled": self._lutris_box.isChecked(),
            "heroic_enabled": self._heroic_box.isChecked(),
            "heroic_dir": self._heroic_edit.text().strip(),
        }
        for attr, edit in self._emu_edits.items():
            changes[attr] = edit.text().strip()
        cfg = replace(self._app.config, **changes)
        self._app.reconfigure(cfg)
