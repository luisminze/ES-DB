"""Edição local de jogos e sessões (overrides no banco derivado).

Menu de contexto (botão direito) e diálogos reutilizados pela Biblioteca e pela
tela do jogo: Editar nome/plataforma/descrição/avaliação, Limpar dados, e edição
do início/fim de cada sessão.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QDateTimeEdit,
                               QInputDialog, QLabel, QMenu, QMessageBox,
                               QVBoxLayout)

from ...domain.calculations import format_duration


def edit_name(app, game) -> bool:
    text, ok = QInputDialog.getText(app.window, "Editar nome", "Nome do jogo:",
                                    text=game.display_title)
    if ok and text.strip():
        app.library.edit_game(game.external_id, title=text.strip())
        app.refresh_pages()
        return True
    return False


def edit_platform(app, game) -> bool:
    plats = sorted({g.platform for g in app.library.games if g.platform})
    if game.platform in plats:
        plats.remove(game.platform)
    options = [game.platform] + plats
    text, ok = QInputDialog.getItem(app.window, "Editar plataforma",
                                    "Plataforma:", options, 0, True)
    if ok and text.strip():
        app.library.edit_game(game.external_id, platform=text.strip())
        app.refresh_pages()
        return True
    return False


def edit_description(app, game) -> bool:
    current = game.metadata.description if game.metadata else ""
    text, ok = QInputDialog.getMultiLineText(
        app.window, "Editar descrição", "Descrição:", current)
    if ok:
        app.library.edit_game(game.external_id, description=text.strip())
        app.refresh_pages()
        return True
    return False


def edit_rating(app, game) -> bool:
    current = (game.metadata.rating * 5) if game.metadata and game.metadata.rating else 0.0
    val, ok = QInputDialog.getDouble(app.window, "Editar avaliação",
                                     "Avaliação (0 a 5 estrelas):", current,
                                     0.0, 5.0, 1)
    if ok:
        app.library.edit_game(game.external_id, rating=val / 5.0)
        app.refresh_pages()
        return True
    return False


def clear_game(app, game) -> bool:
    resp = QMessageBox.warning(
        app.window, "Limpar dados do jogo",
        f"Apagar PERMANENTEMENTE todas as sessões gravadas de "
        f"“{game.display_title}”?\n\nEsta ação não pode ser desfeita.",
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if resp != QMessageBox.Yes:
        return False
    app.library.clear_game(game.external_id)
    app.refresh_pages()
    return True


def build_context_menu(app, game, parent=None) -> QMenu:
    """Menu de contexto do jogo: Editar (submenu) + Limpar dados."""
    menu = QMenu(parent)
    edit = menu.addMenu("Editar")
    edit.addAction("Editar nome", lambda: edit_name(app, game))
    edit.addAction("Editar plataforma", lambda: edit_platform(app, game))
    edit.addAction("Editar descrição", lambda: edit_description(app, game))
    edit.addAction("Editar avaliação", lambda: edit_rating(app, game))
    menu.addSeparator()
    menu.addAction("Limpar dados", lambda: clear_game(app, game))
    return menu


class SessionEditDialog(QDialog):
    """Edita início e fim de uma sessão; a duração é recalculada."""

    def __init__(self, app, session) -> None:
        super().__init__(app.window)
        self._app = app
        self._session = session
        self.setWindowTitle("Editar sessão")
        self.setStyleSheet(app.window.styleSheet())
        self.setObjectName("Panel")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(8)

        lay.addWidget(QLabel("Início:"))
        self._start = QDateTimeEdit()
        self._start.setDisplayFormat("dd/MM/yyyy HH:mm:ss")
        self._start.setCalendarPopup(True)
        self._start.setDateTime(QDateTime.fromSecsSinceEpoch(
            int(session.started_at.timestamp())))
        lay.addWidget(self._start)

        lay.addWidget(QLabel("Fim:"))
        self._end = QDateTimeEdit()
        self._end.setDisplayFormat("dd/MM/yyyy HH:mm:ss")
        self._end.setCalendarPopup(True)
        self._end.setDateTime(QDateTime.fromSecsSinceEpoch(
            int(session.ended_at.timestamp())))
        lay.addWidget(self._end)

        self._dur = QLabel()
        self._dur.setObjectName("CardMeta")
        lay.addWidget(self._dur)
        self._start.dateTimeChanged.connect(self._update_dur)
        self._end.dateTimeChanged.connect(self._update_dur)
        self._update_dur()

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def _secs(self) -> int:
        return max(0, self._end.dateTime().toSecsSinceEpoch()
                   - self._start.dateTime().toSecsSinceEpoch())

    def _update_dur(self) -> None:
        self._dur.setText(f"Tempo total: {format_duration(self._secs())}")

    def _save(self) -> None:
        tz = self._app.tz
        start = datetime.fromtimestamp(
            self._start.dateTime().toSecsSinceEpoch(), tz)
        end = datetime.fromtimestamp(
            self._end.dateTime().toSecsSinceEpoch(), tz)
        if end < start:
            QMessageBox.warning(self, "Sessão inválida",
                                "O fim não pode ser antes do início.")
            return
        self._app.library.update_session(self._session.external_id, start, end)
        self._app.refresh_pages()
        self.accept()
