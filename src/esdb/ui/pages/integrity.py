"""Página de Integridade — qualidade e transparência dos dados (MAIN.md RF-09)."""

from __future__ import annotations

from collections import Counter

from PySide6.QtWidgets import (QGridLayout, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from ...domain.models import DurationKind
from ..widgets import section_title, stat_tile
from .base import clear_layout, empty_label, scroll_container

_LABELS = {
    "duplicate_id": "IDs duplicados",
    "orphan_session": "Sessões órfãs (sem jogo)",
    "invalid_timestamp": "Timestamp inválido",
    "negative_duration": "Duração negativa",
    "duration_mismatch": "Duração divergente",
    "source": "Falha de fonte",
}


class IntegrityPage(QWidget):
    def __init__(self, app) -> None:
        super().__init__()
        self._app = app
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._area, self._content, self._lay = scroll_container()
        outer.addWidget(self._area)

    def update_view(self) -> None:
        clear_layout(self._lay)
        lib = self._app.library
        if lib is None:
            self._lay.addWidget(empty_label("Sem fonte configurada."))
            self._lay.addStretch()
            return
        issues = lib.result.issues
        counts = Counter(i.type for i in issues)

        tiles = QGridLayout()
        tiles.setSpacing(12)
        quick = sum(1 for s in lib.sessions if s.kind is DurationKind.QUICK_LAUNCH)
        summary = [
            (str(len(lib.sessions)), "Sessões importadas", True),
            (str(quick), "Inícios rápidos (0s)", False),
            (str(len(issues)), "Problemas listados", False),
        ]
        for i, (v, lab, acc) in enumerate(summary):
            tiles.addWidget(stat_tile(v, lab, acc), 0, i)
        self._lay.addLayout(tiles)

        if not issues:
            self._lay.addWidget(empty_label(
                "Nenhum problema de integridade encontrado. Sessões de duração "
                "zero são inícios rápidos e contam apenas como sessões."))
            self._lay.addStretch()
            return

        self._lay.addWidget(section_title("Resumo por tipo"))
        grid = QGridLayout()
        grid.setSpacing(10)
        for i, (kind, n) in enumerate(sorted(counts.items(),
                                             key=lambda kv: -kv[1])):
            grid.addWidget(stat_tile(str(n), _LABELS.get(kind, kind)), i // 3, i % 3)
        self._lay.addLayout(grid)

        self._lay.addWidget(section_title("Detalhes"))
        table = QTableWidget(len(issues), 3)
        table.setHorizontalHeaderLabels(["ID da sessão", "Tipo", "Detalhe"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        table.setColumnWidth(0, 120)
        table.setColumnWidth(1, 220)
        for row, issue in enumerate(issues):
            table.setItem(row, 0, QTableWidgetItem(str(issue.external_id)))
            table.setItem(row, 1, QTableWidgetItem(_LABELS.get(issue.type, issue.type)))
            table.setItem(row, 2, QTableWidgetItem(issue.details))
        table.setMinimumHeight(260)
        self._lay.addWidget(table)
        self._lay.addStretch()
