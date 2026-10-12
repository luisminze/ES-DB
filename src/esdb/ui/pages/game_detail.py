"""Diálogo de detalhes do jogo — MAIN.md RF-05 (metadados + sessões + screenshots)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QGridLayout, QHBoxLayout, QLabel,
                               QMessageBox, QPushButton, QScrollArea,
                               QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget)

from ...domain.calculations import format_duration
from ...domain.models import Game
from ..widgets import cover_fit_label, cover_label, section_title, stat_tile


class GameDetailDialog(QDialog):
    def __init__(self, app, game: Game) -> None:
        super().__init__(app.window)
        self._app = app
        self._game = game
        self.setWindowTitle(game.display_title)
        self.resize(760, 680)
        self.setObjectName("Panel")
        self.setStyleSheet(app.window.styleSheet())
        sessions = app.library.sessions_for_game(game.external_id)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

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
        remove_btn = QPushButton("Remover")
        remove_btn.setObjectName("ChromeBtn")
        remove_btn.setToolTip("Remove o jogo da biblioteca (as sessões são mantidas)")
        remove_btn.clicked.connect(self._remove)
        title_row.addWidget(remove_btn, 0, Qt.AlignTop)
        clear_btn = QPushButton("Limpar dados")
        clear_btn.setObjectName("ChromeBtn")
        clear_btn.setToolTip("Apaga permanentemente as sessões gravadas deste jogo")
        clear_btn.clicked.connect(self._clear)
        title_row.addWidget(clear_btn, 0, Qt.AlignTop)
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
        root.addLayout(head)

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
        root.addLayout(tiles)

        root.addWidget(section_title("Histórico de sessões"))
        table = QTableWidget(len(sessions), 3)
        table.setHorizontalHeaderLabels(["Início", "Fim", "Duração"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        table.setColumnWidth(0, 300)
        table.setColumnWidth(1, 300)
        for row, s in enumerate(sessions):
            kind = "" if s.is_valid else f"  ({s.kind.value})"
            table.setItem(row, 0, QTableWidgetItem(
                s.started_at.astimezone(app.tz).strftime("%d/%m/%Y %H:%M")))
            table.setItem(row, 1, QTableWidgetItem(
                s.ended_at.astimezone(app.tz).strftime("%d/%m/%Y %H:%M")))
            table.setItem(row, 2, QTableWidgetItem(
                format_duration(s.duration_seconds) + kind))
        root.addWidget(table, 1)

        shots = app.library.screenshots_for(game)
        if shots:
            root.addWidget(section_title(f"Screenshots ({len(shots)})"))
            strip = QHBoxLayout()
            for path in shots[:6]:
                strip.addWidget(cover_label(path, game.display_title, 160, 90))
            strip.addStretch()
            holder = QWidget()
            holder.setLayout(strip)
            root.addWidget(holder)

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
