"""Diálogo de detalhes do jogo — metadados + sessões (editáveis) + screenshots."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QGridLayout, QHBoxLayout, QLabel,
                               QMessageBox, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from ...domain.calculations import format_duration
from ...domain.models import Game
from ..widgets import cover_fit_label, cover_label, section_title, stat_tile
from .base import clear_layout
from .game_edit import (SessionEditDialog, edit_cover, edit_description,
                        edit_name, edit_platform, edit_rating, remove_game,
                        reset_cover)


class GameDetailDialog(QDialog):
    def __init__(self, app, game: Game) -> None:
        super().__init__(app.window)
        self._app = app
        self._game = game
        self.resize(760, 680)
        self.setObjectName("Panel")
        self.setStyleSheet(app.window.styleSheet())
        # Moldura do Qt Designer (ui/designer/game_detail.ui) com placeholder.
        from ..uiloader import load_ui
        form = load_ui("game_detail.ui", self)
        shell = QVBoxLayout(self)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.addWidget(form)
        host = form.findChild(QWidget, "pageContent")
        self._root = QVBoxLayout(host)
        self._root.setContentsMargins(20, 20, 20, 20)
        self._root.setSpacing(14)
        self._rebuild()

    # ------------------------------------------------------------- render
    def _rebuild(self) -> None:
        game = self._app.library.games_by_id.get(self._game.external_id)
        if game is None:  # removido/limpo enquanto aberto
            self.accept()
            return
        self._game = game
        self.setWindowTitle(game.display_title)
        clear_layout(self._root)

        head = QHBoxLayout()
        head.setSpacing(16)
        head.addWidget(cover_fit_label(game.cover_path, game.display_title, 140),
                       0, Qt.AlignTop)
        info = QVBoxLayout()
        title_row = QHBoxLayout()
        title = QLabel(game.display_title)
        title.setObjectName("PageTitle")
        title.setWordWrap(True)
        title_row.addWidget(title, 1)
        for text, slot, tip in (
            ("Editar", self._edit_menu, "Editar nome, plataforma, descrição, avaliação"),
            ("Remover", self._remove, "Remove da biblioteca (mantém as sessões)"),
            ("Limpar dados", self._clear, "Apaga permanentemente as sessões"),
        ):
            b = QPushButton(text)
            b.setObjectName("ChromeBtn")
            b.setToolTip(tip)
            b.clicked.connect(slot)
            title_row.addWidget(b, 0, Qt.AlignTop)
        info.addLayout(title_row)
        plat = QLabel(f"{game.platform}  ·  {game.system}")
        plat.setObjectName("PageSubtitle")
        info.addWidget(plat)
        if game.metadata:
            meta = game.metadata
            bits = [b for b in (meta.genre, meta.developer, meta.publisher) if b]
            if meta.release_date:
                bits.append(str(meta.release_date.year))
            if meta.rating is not None:
                bits.append(f"★ {meta.rating * 5:.1f}")
            if bits:
                tags = QLabel("  ·  ".join(bits))
                tags.setObjectName("CardMeta")
                tags.setWordWrap(True)
                info.addWidget(tags)
            if meta.description:
                desc = QLabel(meta.description)
                desc.setObjectName("CardMeta")
                desc.setWordWrap(True)
                desc.setMaximumHeight(140)
                info.addWidget(desc)
        info.addStretch()
        head.addLayout(info, 1)
        self._root.addLayout(head)

        sessions = self._app.library.sessions_for_game(game.external_id)
        durations = [s.duration_seconds for s in sessions if s.is_valid]
        tiles = QGridLayout()
        tiles.setSpacing(10)
        stats = [
            (format_duration(game.total_seconds), "Tempo total", True),
            (str(game.session_count), "Sessões", False),
            (format_duration(max(durations) if durations else 0), "Maior sessão", False),
            (format_duration((sum(durations) / len(durations)) if durations else 0),
             "Média", False),
        ]
        for i, (v, lab, acc) in enumerate(stats):
            tiles.addWidget(stat_tile(v, lab, acc), 0, i)
        self._root.addLayout(tiles)

        shead = QHBoxLayout()
        shead.addWidget(section_title("Histórico de sessões"))
        hint = QLabel("duplo-clique: editar · botão direito: apagar")
        hint.setObjectName("CardMeta")
        shead.addWidget(hint)
        shead.addStretch()
        recalc = QPushButton("Recalcular tempos")
        recalc.setObjectName("ChromeBtn")
        recalc.setToolTip("Recalcula a duração de todas as sessões pelos horários "
                          "e sincroniza o tempo total")
        recalc.clicked.connect(self._recalc)
        shead.addWidget(recalc)
        self._root.addLayout(shead)

        self._sessions = sessions
        table = QTableWidget(len(sessions), 3)
        table.setHorizontalHeaderLabels(["Início", "Fim", "Duração"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(
            lambda pos, t=table: self._session_menu(t, pos))
        table.horizontalHeader().setStretchLastSection(True)
        table.setColumnWidth(0, 300)
        table.setColumnWidth(1, 300)
        for row, s in enumerate(sessions):
            kind = "" if s.is_valid else f"  ({s.kind.value})"
            table.setItem(row, 0, QTableWidgetItem(
                s.started_at.astimezone(self._app.tz).strftime("%d/%m/%Y %H:%M")))
            table.setItem(row, 1, QTableWidgetItem(
                s.ended_at.astimezone(self._app.tz).strftime("%d/%m/%Y %H:%M")))
            table.setItem(row, 2, QTableWidgetItem(
                format_duration(s.duration_seconds) + kind))
        table.cellDoubleClicked.connect(self._edit_session)
        self._root.addWidget(table, 1)

        shots = self._app.library.screenshots_for(game)
        if shots:
            self._root.addWidget(section_title(f"Screenshots ({len(shots)})"))
            strip = QHBoxLayout()
            for path in shots[:6]:
                strip.addWidget(cover_label(path, game.display_title, 160, 90))
            strip.addStretch()
            holder = QWidget()
            holder.setLayout(strip)
            self._root.addWidget(holder)

    # ------------------------------------------------------------- actions
    def _edit_menu(self) -> None:
        from PySide6.QtGui import QCursor
        from PySide6.QtWidgets import QMenu
        g = self._game
        menu = QMenu(self)
        menu.addAction("Editar nome", lambda: self._after(edit_name(self._app, g)))
        menu.addAction("Editar plataforma",
                       lambda: self._after(edit_platform(self._app, g)))
        menu.addAction("Editar capa", lambda: self._after(edit_cover(self._app, g)))
        menu.addAction("Restaurar capa padrão",
                       lambda: self._after(reset_cover(self._app, g)))
        menu.addAction("Editar descrição",
                       lambda: self._after(edit_description(self._app, g)))
        menu.addAction("Editar avaliação",
                       lambda: self._after(edit_rating(self._app, g)))
        menu.addSeparator()
        menu.addAction("Remover jogo", self._remove_from_menu)
        menu.exec(QCursor.pos())

    def _remove_from_menu(self) -> None:
        if remove_game(self._app, self._game):
            self.accept()

    def _after(self, changed: bool) -> None:
        if changed:
            self._rebuild()

    def _edit_session(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._sessions):
            if SessionEditDialog(self._app, self._sessions[row]).exec():
                self._rebuild()

    def _session_menu(self, table, pos) -> None:
        from PySide6.QtWidgets import QMenu
        row = table.rowAt(pos.y())
        if not (0 <= row < len(self._sessions)):
            return
        session = self._sessions[row]
        menu = QMenu(self)
        menu.addAction("Editar início/fim", lambda: self._edit_session(row, 0))
        menu.addAction("Apagar sessão", lambda: self._delete_session(session))
        menu.exec(table.viewport().mapToGlobal(pos))

    def _delete_session(self, session) -> None:
        resp = QMessageBox.warning(
            self, "Apagar sessão",
            "Apagar PERMANENTEMENTE esta sessão?\n\n"
            f"{session.started_at.astimezone(self._app.tz).strftime('%d/%m/%Y %H:%M')}"
            f" — {format_duration(session.duration_seconds)}",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if resp != QMessageBox.Yes:
            return
        self._app.library.delete_session(session.external_id)
        self._app.refresh_pages()
        self._rebuild()

    def _recalc(self) -> None:
        self._app.library.recalc_sessions(self._game.external_id)
        self._app.refresh_pages()
        self._rebuild()

    def _remove(self) -> None:
        resp = QMessageBox.question(
            self, "Remover jogo",
            f"Remover “{self._game.display_title}” da biblioteca?\n\n"
            "O jogo deixa de aparecer; as sessões gravadas são mantidas na fonte "
            "e ele reaparece se voltar a ser jogado.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if resp != QMessageBox.Yes:
            return
        self._app.library.hide_game(self._game.external_id)
        self._app.refresh_pages()
        self.accept()

    def _clear(self) -> None:
        resp = QMessageBox.warning(
            self, "Limpar dados do jogo",
            f"Apagar PERMANENTEMENTE todas as sessões gravadas de "
            f"“{self._game.display_title}”?\n\n"
            "Esta ação não pode ser desfeita. O jogo reaparece se voltar a ser "
            "jogado.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if resp != QMessageBox.Yes:
            return
        self._app.library.clear_game(self._game.external_id)
        self._app.refresh_pages()
        self.accept()
