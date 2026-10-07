"""Shell Playnite/Helium: barra superior, pílulas e painel de conteúdo."""

from __future__ import annotations

from datetime import timedelta

import sys

from PySide6.QtCore import QProcess, QSize, Qt
from PySide6.QtGui import QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (QApplication, QButtonGroup, QComboBox,
                               QHBoxLayout, QLabel, QLineEdit, QMainWindow,
                               QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from ..config import AppConfig, save_config, stats_home
from ..conquistas.scanner import ConquistasService
from ..data.library import Library
from ..domain.periods import PRESETS, build_period
from .filter_dialog import FilterPanel
from .pages.achievements import AchievementsPage
from .pages.activity import ActivityPage
from .pages.game_detail import GameDetailDialog
from .pages.integrity import IntegrityPage
from .pages.library import LibraryPage
from .pages.retrospective import RetrospectivePage
from .pages.settings import SettingsPage
from .pages.statistics import StatisticsPage
from .pages.summary import SummaryPage
from .theme import build_qss, palette
from .widgets import nav_icon
from ..resources import icon_file

PILLS = [
    ("library", "Biblioteca"),
    ("statistics", "Estatísticas"),
    ("activity", "Atividade"),
    ("achievements", "Conquistas"),
    ("retrospective", "Retrospectiva"),
]
GHOSTS = [("summary", "Resumo")]
PERIOD_PAGES = {"summary", "statistics", "library"}
TITLES = {
    "summary": "Resumo", "statistics": "Estatísticas", "activity": "Atividade",
    "achievements": "Conquistas", "retrospective": "Retrospectiva",
    "library": "Biblioteca", "settings": "Configurações",
    "integrity": "Integridade",
}


class MainWindow(QMainWindow):
    """Também atua como controlador: expõe config, library, period e filtros."""

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.window = self
        self.config = config
        self.tz = config.tzinfo()
        self.library: Library | None = None
        self._conquistas_cache: list | None = None
        self.period = build_period("all", self.tz)
        self.search_text = ""
        self.filters = {"platforms": set(), "genres": set(), "developers": set(),
                        "options": {}}
        self._current = "summary"

        self.setWindowTitle("ES-DB")
        _icon = icon_file()
        if _icon:
            self.setWindowIcon(QIcon(_icon))
        self.resize(1280, 820)
        self._build_ui()
        self._apply_theme()
        self.reload_library()
        self.navigate("library")

    # --------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        chrome = QWidget()
        chrome.setObjectName("Chrome")
        root = QVBoxLayout(chrome)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_topbar())

        body = QHBoxLayout()
        body.setContentsMargins(12, 12, 12, 12)
        body.setSpacing(12)
        body.addWidget(self._build_nav())
        body.addWidget(self._build_panel(), 1)
        wrap = QWidget()
        wrap.setLayout(body)
        root.addWidget(wrap, 1)
        self.setCentralWidget(chrome)

        QShortcut(QKeySequence("Ctrl+F"), self, self._search.setFocus)
        QShortcut(QKeySequence("Ctrl+R"), self, self.refresh_data)

    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(58)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 8, 16, 8)
        lay.setSpacing(8)
        _icon = icon_file()
        if _icon:
            mark = QLabel()
            pix = QPixmap(_icon)
            if not pix.isNull():
                mark.setPixmap(pix.scaledToHeight(34, Qt.SmoothTransformation))
                mark.setToolTip("ES-DB")
                lay.addWidget(mark)
        logo = QLabel()
        logo.setObjectName("Logo")
        logo.setTextFormat(Qt.RichText)
        logo.setText("ES<font color='#EB5E54'>-</font>DB")
        lay.addWidget(logo)
        self._search = QLineEdit()
        self._search.setObjectName("SearchBox")
        self._search.setPlaceholderText("Buscar jogos…")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._on_search)
        self._search.setMaximumWidth(360)
        lay.addWidget(self._search)
        lay.addStretch(1)

        accent = palette(self.config.theme)["accent"]
        isize = 26
        for icon, tip, name, handler in (
            ("funnel", "Filtros", "Filtros", self.open_filters),
            ("refresh", "Atualizar (Ctrl+R)", "Atualizar", self.refresh_data),
            ("gear", "Configurações", "Configurações",
             lambda: self.navigate("settings")),
        ):
            btn = QPushButton()
            btn.setObjectName("IconBtn")
            btn.setIcon(nav_icon(icon, accent if icon == "funnel" else "#E8EAED",
                                 isize))
            btn.setIconSize(QSize(isize, isize))
            btn.setToolTip(tip)
            btn.setAccessibleName(name)
            btn.clicked.connect(handler)
            lay.addWidget(btn)
            if icon == "funnel":
                self._filters_btn = btn
        return bar

    def _build_nav(self) -> QWidget:
        nav = QWidget()
        nav.setObjectName("Nav")
        nav.setFixedWidth(230)
        lay = QVBoxLayout(nav)
        lay.setContentsMargins(0, 12, 0, 12)
        lay.setSpacing(0)
        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        self._nav_buttons: dict[str, QPushButton] = {}
        pills = [(k, lbl) for k, lbl in PILLS
                 if k != "achievements" or self.config.achievements_enabled]
        for key, label in pills:
            btn = QPushButton(label)
            btn.setObjectName("NavPill")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _=False, k=key: self.navigate(k))
            self._nav_group.addButton(btn)
            self._nav_buttons[key] = btn
            lay.addWidget(btn)
        lay.addStretch()
        for key, label in GHOSTS:
            btn = QPushButton(label)
            btn.setObjectName("NavGhost")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _=False, k=key: self.navigate(k))
            self._nav_group.addButton(btn)
            self._nav_buttons[key] = btn
            lay.addWidget(btn)
        return nav

    def _build_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("Panel")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)
        header = QHBoxLayout()
        self._title = QLabel("Resumo")
        self._title.setObjectName("PageTitle")
        header.addWidget(self._title)
        header.addStretch()
        self._period_combo = QComboBox()
        for key, label in PRESETS:
            self._period_combo.addItem(label, key)
        self._period_combo.setCurrentIndex(len(PRESETS) - 1)  # todo o histórico
        self._period_combo.currentIndexChanged.connect(self._on_period)
        self._period_label = QLabel("Período:")
        header.addWidget(self._period_label)
        header.addWidget(self._period_combo)
        lay.addLayout(header)

        self._stack = QStackedWidget()
        self.pages = {
            "summary": SummaryPage(self),
            "statistics": StatisticsPage(self),
            "activity": ActivityPage(self),
            "achievements": AchievementsPage(self),
            "retrospective": RetrospectivePage(self),
            "library": LibraryPage(self),
            "settings": SettingsPage(self),
            "integrity": IntegrityPage(self),
        }
        for page in self.pages.values():
            self._stack.addWidget(page)
        lay.addWidget(self._stack, 1)
        return panel

    # ----------------------------------------------------------- actions
    def _apply_theme(self) -> None:
        self.setStyleSheet(build_qss(palette(self.config.theme)))

    def reload_library(self) -> None:
        if self.library is not None:
            try:
                self.library.store.close()
            except Exception:
                pass
        if self.config.is_configured():
            derived = str(stats_home() / "derived" / "esdb.db")
            self.library = Library(self.config.session_db, self.config.esde_home,
                                   self.tz, derived)
            self.library.load()
        else:
            self.library = None

    def refresh_data(self) -> None:
        if self.library is not None:
            self.library.load()
        self._conquistas_cache = None
        self.refresh_pages()

    def conquistas_games(self) -> list:
        if not self.config.achievements_enabled:
            return []
        if self._conquistas_cache is None:
            service = ConquistasService(self.config.rpcs3_dir,
                                        self.config.shadps4_dir,
                                        self.config.xenia_dir)
            try:
                self._conquistas_cache = service.scan()
            except OSError:
                self._conquistas_cache = []
        return self._conquistas_cache

    def reconfigure(self, cfg: AppConfig) -> None:
        # Ligar/desligar as Conquistas muda a navegação: reinicia o app.
        toggled = cfg.achievements_enabled != self.config.achievements_enabled
        self.config = cfg
        self.tz = cfg.tzinfo()
        save_config(cfg)
        if toggled:
            self._restart()
            return
        self._apply_theme()
        self.filters = {"platforms": set(), "genres": set(), "developers": set(),
                        "options": {}}
        self._conquistas_cache = None
        self.reload_library()
        self.navigate("library")

    def _restart(self) -> None:
        """Reinicia o aplicativo (usado ao ligar/desligar as Conquistas)."""
        QProcess.startDetached(sys.executable, ["-m", "esdb"])
        QApplication.instance().quit()

    def navigate(self, key: str) -> None:
        self._current = key
        self._stack.setCurrentWidget(self.pages[key])
        self._title.setText(TITLES.get(key, key))
        btn = self._nav_buttons.get(key)
        if btn is not None:
            btn.setChecked(True)
        show_period = key in PERIOD_PAGES
        self._period_combo.setVisible(show_period)
        self._period_label.setVisible(show_period)
        self.pages[key].update_view()

    def refresh_pages(self) -> None:
        self.pages[self._current].update_view()

    def open_filters(self) -> None:
        if self.library is None:
            return
        FilterPanel(self).open_under(self._filters_btn)

    def open_game(self, game) -> None:
        if self.library is not None:
            GameDetailDialog(self, game).exec()

    def _on_search(self, text: str) -> None:
        self.search_text = text.strip().lower()
        if self._current != "library":
            self.navigate("library")
        else:
            self.pages["library"].update_view()

    def _on_period(self, _index: int) -> None:
        key = self._period_combo.currentData()
        self.period = build_period(key, self.tz)
        self.refresh_pages()

    # ------------------------------------------------------------ filters
    def filtered_games(self):
        if self.library is None:
            return []
        from datetime import datetime
        games = self.library.games
        f = self.filters
        text = self.search_text
        recent_cut = datetime.now(self.tz) - timedelta(days=7)
        out = []
        for g in games:
            if text and text not in g.display_title.lower() \
                    and text not in g.platform.lower() \
                    and text not in g.rom_basename.lower():
                continue
            if f["platforms"] and g.platform not in f["platforms"]:
                continue
            if f["genres"] and not (g.metadata and g.metadata.genre in f["genres"]):
                continue
            if f["developers"] and not (g.metadata and g.metadata.developer in f["developers"]):
                continue
            opts = f["options"]
            if opts.get("only_cover") and not g.cover_path:
                continue
            if opts.get("only_screenshots") and not self.library.screenshots_for(g):
                continue
            if opts.get("recent7") and (g.last_played_at is None
                                        or g.last_played_at < recent_cut):
                continue
            out.append(g)
        return out

    def library_scope_label(self) -> str:
        plats = self.filters["platforms"]
        if len(plats) == 1:
            return next(iter(plats))
        if len(plats) > 1:
            return f"{len(plats)} plataformas"
        return "Todos os jogos"
