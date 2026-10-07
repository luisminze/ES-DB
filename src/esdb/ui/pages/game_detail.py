"""Diálogo de detalhes do jogo — MAIN.md RF-05 (metadados + sessões + screenshots)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QGridLayout, QHBoxLayout, QLabel,
                               QScrollArea, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from ...domain.calculations import format_duration
from ...domain.models import Game
from ..widgets import cover_label, section_title, stat_tile


class GameDetailDialog(QDialog):
    def __init__(self, app, game: Game) -> None:
        super().__init__(app.window)
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
        head.addWidget(cover_label(game.cover_path, game.display_title, 140, 210))
        info = QVBoxLayout()
        title = QLabel(game.display_title)
        title.setObjectName("PageTitle")
        title.setWordWrap(True)
        info.addWidget(title)
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
