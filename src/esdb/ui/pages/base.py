"""Utilidades compartilhadas pelas páginas."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QLabel, QLayout, QScrollArea, QVBoxLayout,
                               QWidget)


def clear_layout(layout: QLayout) -> None:
    """Remove e destrói todos os itens de um layout (para redesenhar)."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
        else:
            child = item.layout()
            if child is not None:
                clear_layout(child)


def scroll_container() -> tuple[QScrollArea, QWidget, QVBoxLayout]:
    """Cria uma área rolável com um conteúdo vertical dentro."""
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    content = QWidget()
    content.setObjectName("ScrollBody")
    lay = QVBoxLayout(content)
    lay.setContentsMargins(0, 0, 8, 8)
    lay.setSpacing(16)
    area.setWidget(content)
    return area, content, lay


def empty_label(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("CardMeta")
    lab.setWordWrap(True)
    return lab
