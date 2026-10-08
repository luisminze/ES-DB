"""Gera um ícone quadrado (512x512) a partir do logo ES, para o AppImage."""

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter

SRC = Path(__file__).resolve().parent.parent / "src" / "esdb" / "resources" / "icon.png"


def main(out_path: str, size: int = 512) -> int:
    src = QImage(str(SRC))
    if src.isNull():
        print(f"ícone de origem ausente: {SRC}", file=sys.stderr)
        return 1
    canvas = QImage(size, size, QImage.Format_ARGB32)
    canvas.fill(QColor(10, 11, 14))          # fundo carvão (combina com o logo)
    scaled = src.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    p = QPainter(canvas)
    p.drawImage((size - scaled.width()) // 2, (size - scaled.height()) // 2, scaled)
    p.end()
    canvas.save(out_path, "PNG")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "esdb.png"))
