"""Tema Playnite/Helium: paleta e folha de estilo (INTERFACE.md §4).

Separa *chrome* (barra + navegação) do **painel de conteúdo escuro**. Acento
vermelho reservado a seleção, foco e ações primárias — nunca única indicação de
estado (a seleção também muda peso/contorno).
"""

from __future__ import annotations

DARK = {
    "chrome_bg": "#0C0D10",
    "chrome_surface": "#141519",
    "panel_bg": "#15171C",
    "panel_surface": "#1C1F26",
    "panel_surface_2": "#232731",
    "text": "#E8EAED",
    "text_dim": "#9BA1AD",
    "text_faint": "#6B7280",
    "border": "#2A2E38",
    "accent": "#EB5E54",
    "accent_dim": "#8E2F28",
    "accent_wash": "#221015",       # fundo de cards com leve tom de acento
}

# Tema claro unificado: tudo claro; separadores usam um branco levemente mais
# escuro (panel_surface_2). Texto escuro, acento vermelho legível sobre branco.
LIGHT = {
    "chrome_bg": "#E7E9ED",
    "chrome_surface": "#FFFFFF",
    "panel_bg": "#F3F4F7",
    "panel_surface": "#FFFFFF",
    "panel_surface_2": "#E9EBEF",   # tom de branco mais escuro, levemente
    "text": "#1B1E24",
    "text_dim": "#596070",
    "text_faint": "#949AA6",
    "border": "#D6D9E0",
    "accent": "#C62C22",
    "accent_dim": "#EBB9B3",
    "accent_wash": "#FBECEA",
}

_ACTIVE: dict[str, str] = DARK


def palette(theme: str) -> dict[str, str]:
    return LIGHT if resolve_theme(theme) == "light" else DARK


def resolve_theme(theme: str) -> str:
    """Resolve 'system' para 'light'/'dark' conforme o SO; repassa os demais."""
    if theme == "light":
        return "light"
    if theme == "dark":
        return "dark"
    # 'system' (ou desconhecido): segue o esquema de cor do sistema operacional.
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            scheme = app.styleHints().colorScheme()
            if scheme == Qt.ColorScheme.Light:
                return "light"
            if scheme == Qt.ColorScheme.Dark:
                return "dark"
    except Exception:
        pass
    return "dark"


def set_active(pal: dict[str, str]) -> None:
    """Registra a paleta em uso, para widgets pintados com QPainter a lerem."""
    global _ACTIVE
    _ACTIVE = pal


def active() -> dict[str, str]:
    return _ACTIVE


def is_light() -> bool:
    return _ACTIVE is LIGHT


def build_qss(p: dict[str, str]) -> str:
    return f"""
    QWidget {{
        color: {p['text']};
        font-size: 14px;
        font-family: "Inter", "Segoe UI", "Noto Sans", sans-serif;
    }}
    QLabel {{ color: {p['text']}; background: transparent; }}
    #Chrome {{ background: {p['chrome_bg']}; }}
    #TopBar {{ background: {p['chrome_surface']}; border-bottom: 1px solid {p['border']}; }}
    #Logo {{ font-size: 18px; font-weight: 800; color: {p['text']}; padding: 0 6px; }}
    #LogoAccent {{ color: {p['accent']}; }}

    #SearchBox {{
        background: {p['chrome_bg']}; border: 1px solid {p['border']};
        border-radius: 16px; padding: 7px 14px; color: {p['text']};
        selection-background-color: {p['accent']};
    }}
    #SearchBox:focus {{ border: 1px solid {p['accent']}; }}

    QPushButton#ChromeBtn {{
        background: {p['chrome_bg']}; border: 1px solid {p['border']};
        border-radius: 16px; padding: 7px 14px; color: {p['text']};
    }}
    QPushButton#ChromeBtn:hover {{ border-color: {p['accent']}; }}
    QPushButton#ChromeBtn:pressed {{ background: {p['panel_surface_2']}; }}

    QPushButton#IconBtn {{
        background: transparent; border: 1px solid transparent;
        border-radius: 12px; padding: 8px; min-width: 30px; min-height: 30px;
    }}
    QPushButton#IconBtn:hover {{
        background: {p['chrome_bg']}; border-color: {p['border']};
    }}
    QPushButton#IconBtn:pressed {{ background: {p['panel_surface_2']}; }}

    #Nav {{ background: {p['chrome_bg']}; }}
    QPushButton#NavPill {{
        text-align: center; background: transparent; border: none;
        border-radius: 9px; padding: 7px 14px; margin: 0 2px;
        color: {p['text_dim']}; font-size: 13px;
    }}
    QPushButton#NavPill:hover {{ background: {p['panel_surface_2']}; color: {p['text']}; }}
    QPushButton#NavPill:checked {{
        background: {p['accent']}; color: white; font-weight: 700;
    }}
    QPushButton#NavGhost {{
        text-align: center; background: transparent; border: none;
        border-radius: 9px; padding: 7px 12px; margin: 0 2px; color: {p['text_faint']};
    }}
    QPushButton#NavGhost:hover {{ color: {p['text']}; }}
    QPushButton#NavGhost:checked {{ color: {p['accent']}; font-weight: 700; }}

    #Panel {{ background: {p['panel_bg']}; border-radius: 16px; }}
    #PageTitle {{ font-size: 24px; font-weight: 800; color: {p['text']}; }}
    #PageSubtitle {{ color: {p['text_dim']}; font-size: 13px; }}
    #SectionTitle {{ font-size: 16px; font-weight: 700; color: {p['text']}; }}

    QComboBox {{
        background: {p['panel_surface']}; border: 1px solid {p['border']};
        border-radius: 10px; padding: 6px 12px; min-height: 20px;
        combobox-popup: 0;
    }}
    QComboBox:hover {{ border-color: {p['accent']}; }}
    QComboBox::drop-down {{
        subcontrol-origin: padding; subcontrol-position: center right;
        width: 22px; border: none; background: transparent;
        margin-right: 4px;
    }}
    QComboBox QAbstractItemView {{
        background: {p['panel_surface']}; border: 1px solid {p['border']};
        border-radius: 8px; selection-background-color: {p['accent']};
        outline: none; padding: 4px;
    }}

    #Tile {{
        background: {p['panel_surface']}; border: 1px solid {p['border']};
        border-radius: 14px;
    }}
    #TileValue {{ font-size: 26px; font-weight: 800; color: {p['text']}; }}
    #TileLabel {{ color: {p['text_dim']}; font-size: 12px; }}
    #TileAccent {{ font-size: 26px; font-weight: 800; color: {p['accent']}; }}

    #Card {{
        background: {p['panel_surface']}; border: 1px solid {p['border']};
        border-radius: 12px;
    }}
    #Card:hover {{ border-color: {p['accent']}; }}
    #CardTitle {{ font-weight: 700; color: {p['text']}; }}
    #CardMeta {{ color: {p['text_dim']}; font-size: 12px; }}
    #Cover {{ border-radius: 8px; background: {p['panel_surface_2']}; }}
    #Placeholder {{
        border-radius: 8px; background: {p['panel_surface_2']};
        color: {p['text_faint']}; font-size: 30px; font-weight: 800;
    }}

    QScrollArea {{ border: none; background: transparent; }}
    #ScrollBody {{ background: {p['panel_bg']}; }}

    /* Identidade da Retrospectiva: carvão + acento vermelho (não Steam). */
    #RadarCard {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 {p['accent_wash']}, stop:0.5 {p['panel_surface']}, stop:1 {p['panel_bg']});
        border: 1px solid {p['border']}; border-left: 3px solid {p['accent']};
        border-radius: 14px;
    }}
    #StreakCard {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {p['accent_wash']}, stop:0.5 {p['panel_surface']}, stop:1 {p['accent_wash']});
        border: 1px solid {p['border']}; border-left: 3px solid {p['accent']};
        border-radius: 14px;
    }}
    #RetroCard {{
        background: {p['panel_surface']}; border: 1px solid {p['border']};
        border-left: 3px solid {p['accent']}; border-radius: 14px;
    }}
    #PodiumRank {{ color: {p['text_dim']}; font-weight: 800; letter-spacing: 1px; }}
    #PodiumWinner {{
        background: {p['panel_surface']};
        border: 1px solid {p['accent']}; border-radius: 12px;
    }}
    #RetroYear {{ color: {p['accent']}; font-size: 40px; font-weight: 900; }}
    #BannerNum {{ color: {p['text']}; font-size: 34px; font-weight: 900; }}
    #DeltaUp {{ color: #4FB15A; font-weight: 700; font-size: 12px; }}
    #DeltaDown {{ color: {p['accent']}; font-weight: 700; font-size: 12px; }}
    #ExploreBadge {{
        background: {p['accent']}; color: white; border-radius: 6px;
        padding: 1px 6px; font-size: 9px; font-weight: 700;
    }}
    #ExplorePct {{ color: {p['text']}; font-weight: 800; }}
    #FilterPanel {{
        background: {p['panel_surface']}; border: 1px solid {p['border']};
        border-top: 3px solid {p['accent']}; border-radius: 12px;
    }}
    #RetroHero {{ font-size: 30px; font-weight: 800; color: {p['text']}; }}
    #KickerText {{ color: {p['accent']}; font-weight: 800; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {p['border']}; border-radius: 5px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: {p['accent_dim']}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}

    QTableWidget {{
        background: {p['panel_surface']}; border: 1px solid {p['border']};
        border-radius: 12px; gridline-color: {p['border']};
        selection-background-color: {p['accent_dim']};
    }}
    QHeaderView::section {{
        background: {p['panel_surface_2']}; color: {p['text_dim']};
        border: none; padding: 8px; font-weight: 600;
    }}
    QTableWidget::item {{ padding: 6px; }}

    #Bar {{ background: {p['panel_surface_2']}; border-radius: 5px; }}
    #BarFill {{ background: {p['accent']}; border-radius: 5px; }}
    #Chip {{
        background: {p['panel_surface_2']}; border: 1px solid {p['border']};
        border-radius: 12px; padding: 3px 10px; color: {p['text_dim']}; font-size: 12px;
    }}
    #Divider {{ color: {p['text_faint']}; font-weight: 700; font-size: 12px; }}
    QCheckBox {{ color: {p['text']}; padding: 3px; }}
    QCheckBox::indicator {{
        width: 16px; height: 16px; border-radius: 4px;
        border: 1px solid {p['border']}; background: {p['panel_surface']};
    }}
    QCheckBox::indicator:checked {{
        background: {p['accent']}; border-color: {p['accent']};
    }}
    QLineEdit {{
        background: {p['panel_surface']}; color: {p['text']};
        border: 1px solid {p['border']}; border-radius: 8px; padding: 6px 10px;
        selection-background-color: {p['accent']};
    }}
    QLineEdit:focus {{ border-color: {p['accent']}; }}
    """
