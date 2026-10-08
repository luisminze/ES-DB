"""Página Retrospectiva — leitura anual estilo "Replay" (RETROSPECTIVA.md §6).

Layout: podium dos jogos mais jogados, indicadores, radar de gêneros ("Você é o
que você joga"), atividade por mês, calendário, distribuição por hora, rankings e
"Sua maior sequência diária" com as capas dos jogos do período.
"""

from __future__ import annotations

import getpass
import math
from collections import defaultdict
from datetime import date, timedelta

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QLinearGradient, QPainter,
                           QPainterPath, QPen, QPolygonF)
from PySide6.QtWidgets import (QComboBox, QFrame, QGridLayout, QHBoxLayout,
                               QLabel, QVBoxLayout, QWidget)

from ...domain.calculations import (Metrics, format_duration, split_by_day,
                                    split_by_month)
from ...domain.year_review import (YearReview, available_years,
                                   compute_year_review)
from ..theme import active, palette
from ..widgets import (cover_fit_label, cover_label, load_cover, ranking_list,
                       section_title, stat_tile)
from .base import clear_layout, empty_label, scroll_container

_MONTHS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set",
           "Out", "Nov", "Dez"]
_MONTHS_FULL = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
                "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
_MONTHS_DOT = ["", "jan.", "fev.", "mar.", "abr.", "mai.", "jun.", "jul.",
               "ago.", "set.", "out.", "nov.", "dez."]
_HEAT = ["#262A33", "#5A2A2A", "#8E2F28", "#C24A3E", "#EB5E54"]
_RADAR = "#EB5E54"
_GAME_COLORS = ["#3BA7AD", "#4FB15A", "#7E8CA0", "#7C5CCB", "#D06B6B",
                "#4A90D9", "#E0A24A", "#C06BB0"]
_OUTROS_COLOR = "#565C66"


def _primary_genre(genre: str) -> str:
    out = genre
    for sep in ("/", ",", ";", "-"):
        out = out.split(sep)[0]
    return out.strip()


class RadarChart(QWidget):
    """Gráfico de teia (radar) dos gêneros mais jogados."""

    def __init__(self, data: list[tuple[str, float]]) -> None:
        super().__init__()
        self._data = data
        self.setMinimumHeight(300)

    def paintEvent(self, _event) -> None:  # noqa: N802
        n = len(self._data)
        if n < 3:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        radius = min(w, h) / 2 - 46
        maxv = max(v for _, v in self._data) or 1.0

        def pt(i: int, r: float) -> QPointF:
            ang = -math.pi / 2 + 2 * math.pi * i / n
            return QPointF(cx + r * math.cos(ang), cy + r * math.sin(ang))

        grid_col = QColor(active()["text"]); grid_col.setAlpha(45)
        p.setPen(QPen(grid_col, 1))
        p.setBrush(Qt.NoBrush)
        for ring in (0.25, 0.5, 0.75, 1.0):
            p.drawPolygon(QPolygonF([pt(i, radius * ring) for i in range(n)]))
        for i in range(n):
            p.drawLine(QPointF(cx, cy), pt(i, radius))

        poly = QPolygonF([pt(i, radius * (v / maxv)) for i, (_, v) in enumerate(self._data)])
        fill = QColor(_RADAR); fill.setAlpha(70)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(QColor(_RADAR), 2))
        p.drawPolygon(poly)
        p.setBrush(QColor("#FFD8D4"))
        p.setPen(Qt.NoPen)
        for i, (_, v) in enumerate(self._data):
            p.drawEllipse(pt(i, radius * (v / maxv)), 3.2, 3.2)

        p.setPen(QColor(active()["text"]))
        font = p.font(); font.setPointSize(8); p.setFont(font)
        for i, (label, _) in enumerate(self._data):
            lp = pt(i, radius + 20)
            p.drawText(QRectF(lp.x() - 70, lp.y() - 12, 140, 24),
                       Qt.AlignCenter, label)


class MonthlyStackedChart(QWidget):
    """Barras empilhadas do tempo por mês, segmentadas por jogo (% do ano).

    Ao passar o mouse, mostra o percentual do mês e a divisão por jogo, com a
    capa do jogo mais jogado naquele mês.
    """

    def __init__(self, breakdown: dict[int, dict[int, float]], year_total: float,
                 games_by_id) -> None:
        super().__init__()
        self._bd = breakdown
        self._total = year_total or 1.0
        self._games = games_by_id
        self._hover: int | None = None
        self._bars: dict[int, QRectF] = {}
        self.setMinimumHeight(380)
        self.setMouseTracking(True)

        agg: dict[int, float] = defaultdict(float)
        for gs in breakdown.values():
            for gid, sec in gs.items():
                agg[gid] += sec
        ranked = sorted(agg, key=lambda k: agg[k], reverse=True)
        self._tracked = ranked[:len(_GAME_COLORS)]
        self._color = {gid: _GAME_COLORS[i] for i, gid in enumerate(self._tracked)}
        self._month_total = {m: sum(breakdown.get(m, {}).values())
                             for m in range(1, 13)}
        maxpct = max((v / self._total * 100 for v in self._month_total.values()),
                     default=0.0)
        self._ymax = max(4, math.ceil(maxpct / 4) * 4)

    # ---------------------------------------------------------- interaction
    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        pos = event.position()
        new = None
        for m, rect in self._bars.items():
            if rect.contains(pos):
                new = m
                break
        if new != self._hover:
            self._hover = new
            self.update()

    def leaveEvent(self, _event) -> None:  # noqa: N802
        if self._hover is not None:
            self._hover = None
            self.update()

    # ---------------------------------------------------------------- paint
    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        pal = active()
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, w, h), 14, 14)
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, QColor(pal["accent_wash"]))
        grad.setColorAt(0.22, QColor(pal["panel_surface"]))
        grad.setColorAt(0.78, QColor(pal["panel_surface"]))
        grad.setColorAt(1.0, QColor(pal["accent_wash"]))
        p.fillPath(path, grad)
        p.setPen(QPen(QColor(pal["border"]), 1))
        p.drawPath(path)
        p.setClipPath(path)

        p.setPen(QColor(pal["text"]))
        tf = QFont(p.font()); tf.setPointSize(14); tf.setBold(True)
        p.setFont(tf)
        p.drawText(QRectF(0, 16, w, 30), Qt.AlignHCenter,
                   "Seu tempo de jogo neste ano, por mês")

        left, top, right, bottom = 60, 56, 20, 40
        px, py = left, top
        pw, ph = w - left - right, h - top - bottom
        small = QFont(p.font()); small.setPointSize(8); small.setBold(False)
        p.setFont(small)
        grid_col = QColor(pal["text"]); grid_col.setAlpha(30)

        steps = 4
        for i in range(steps + 1):
            yy = py + ph - ph * i / steps
            p.setPen(grid_col)
            p.drawLine(QPointF(px, yy), QPointF(px + pw, yy))
            p.setPen(QColor(pal["text_dim"]))
            label = "< 1%" if i == 0 else f"{int(self._ymax * i / steps)}%"
            p.drawText(QRectF(0, yy - 10, left - 8, 20),
                       Qt.AlignRight | Qt.AlignVCenter, label)

        bw = pw / 12
        barw = bw * 0.56
        self._bars.clear()
        for m in range(1, 13):
            cx = px + bw * (m - 0.5)
            self._bars[m] = QRectF(cx - bw / 2, py, bw, ph)
            if self._hover == m:
                band = QColor(pal["text"]); band.setAlpha(22)
                mark = QColor(pal["accent"])
                p.fillRect(QRectF(cx - barw / 2 - 3, py, barw + 6, ph), band)
                p.fillRect(QRectF(cx - 1.5, py, 3, ph), mark)
            gs = self._bd.get(m, {})
            y_cursor = py + ph
            x0 = cx - barw / 2
            outros = sum(sec for gid, sec in gs.items() if gid not in self._color)
            for gid in self._tracked:
                sec = gs.get(gid, 0.0)
                if sec <= 0:
                    continue
                seg_h = ph * (sec / self._total * 100) / self._ymax
                p.fillRect(QRectF(x0, y_cursor - seg_h, barw, seg_h),
                           QColor(self._color[gid]))
                y_cursor -= seg_h
            if outros > 0:
                seg_h = ph * (outros / self._total * 100) / self._ymax
                p.fillRect(QRectF(x0, y_cursor - seg_h, barw, seg_h),
                           QColor(_OUTROS_COLOR))
            p.setPen(QColor(pal["text_dim"]))
            p.drawText(QRectF(cx - bw / 2, py + ph + 4, bw, 18),
                       Qt.AlignHCenter, _MONTHS_DOT[m])

        if self._hover is not None:
            self._draw_tooltip(p, w, h, px, py, pw, ph, bw)

    def _draw_tooltip(self, p, w, h, px, py, pw, ph, bw) -> None:
        m = self._hover
        gs = self._bd.get(m, {})
        mt = self._month_total.get(m, 0.0)
        month_pct = mt / self._total * 100
        pct_txt = "< 1%" if 0 < month_pct < 1 else f"{month_pct:.0f}%"
        items = sorted(gs.items(), key=lambda kv: kv[1], reverse=True)
        lines: list[tuple[str, str]] = [(pct_txt, f" em {_MONTHS_FULL[m]}")]
        cover_path = None
        if mt > 0:
            lines.append(("Desse tempo:", ""))
            top = items[:2]
            if top:
                g0 = self._games.get(top[0][0])
                cover_path = g0.cover_path if g0 else None
            for gid, sec in top:
                g = self._games.get(gid)
                nm = g.display_title if g else "—"
                lines.append((f"{sec / mt * 100:.0f}%", f" em {nm}"))
            others = sum(v for _, v in items[2:])
            if others > 0:
                lines.append((f"{others / mt * 100:.0f}%", " em outros jogos"))

        pad = 12
        cover_w = 46 if cover_path else 0
        line_h = 18
        tw = 258
        th = pad * 2 + line_h * len(lines)
        th = max(th, pad * 2 + 64) if cover_path else th
        bar = self._bars[m]
        tx = bar.center().x() + bar.width() / 2
        if tx + tw > px + pw:
            tx = bar.center().x() - bar.width() / 2 - tw
        tx = max(px, min(tx, px + pw - tw))
        ty = max(py + 6, min(py + ph / 3, py + ph - th))

        pal = active()
        panel = QPainterPath()
        panel.addRoundedRect(QRectF(tx, ty, tw, th), 10, 10)
        p.fillPath(panel, QColor(pal["panel_surface"]))
        pen = QPen(QColor(pal["accent"]))
        pen.setWidthF(1.2)
        p.setPen(pen)
        p.drawPath(panel)

        text_x = tx + pad
        if cover_path:
            pix = load_cover(cover_path, cover_w, 62)
            if pix is not None:
                p.drawPixmap(int(tx + pad), int(ty + pad), pix)
            text_x = tx + pad + cover_w + 10

        y = ty + pad + 12
        for strong, rest in lines:
            fx = QFont(p.font())
            fx.setBold(True)
            p.setFont(fx)
            # números/percentuais em vermelho (identidade); rótulos no texto normal
            p.setPen(QColor(pal["text"]) if strong.endswith(":") else QColor(pal["accent"]))
            p.drawText(QPointF(text_x, y), strong)
            sw = p.fontMetrics().horizontalAdvance(strong)
            fx.setBold(False)
            p.setFont(fx)
            p.setPen(QColor(pal["text_dim"]))
            # quebra simples do restante para caber
            p.drawText(QRectF(text_x + sw, y - 12, tw - (text_x - tx) - pad - sw, 16),
                       Qt.AlignLeft | Qt.AlignVCenter, rest)
            y += line_h


class ExploreGrid(QWidget):
    """Grade responsiva de capas — colunas calculadas pela largura (uniforme)."""

    CELL_W = 104
    SPACING = 16

    def __init__(self, items: list[dict]) -> None:
        super().__init__()
        self._items = items
        self._cols = 0
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(self.SPACING)
        self._grid.setAlignment(Qt.AlignTop)
        self._relayout(force=True)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._relayout()

    def _columns(self) -> int:
        width = self.width()
        return max(1, (width + self.SPACING) // (self.CELL_W + self.SPACING))

    def _relayout(self, force: bool = False) -> None:
        cols = self._columns()
        if cols == self._cols and not force:
            return
        self._cols = cols
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        for c in range(40):
            self._grid.setColumnStretch(c, 0)
        for i, item in enumerate(self._items):
            self._grid.addWidget(self._cell(item), i // cols, i % cols,
                                 Qt.AlignHCenter | Qt.AlignTop)
        for c in range(cols):
            self._grid.setColumnStretch(c, 1)

    def _cell(self, item: dict) -> QWidget:
        cell = QWidget()
        cell.setFixedWidth(self.CELL_W)
        cv = QVBoxLayout(cell)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(3)
        cv.addWidget(cover_fit_label(item["cover"], item["title"], 92),
                     0, Qt.AlignHCenter)
        if item["first"]:
            badge = QLabel("1ª VEZ")
            badge.setObjectName("ExploreBadge")
            badge.setAlignment(Qt.AlignHCenter)
            cv.addWidget(badge, 0, Qt.AlignHCenter)
        info = QLabel(item["info"])
        info.setObjectName("ExplorePct")
        info.setAlignment(Qt.AlignHCenter)
        cv.addWidget(info)
        return cell


class RetrospectivePage(QWidget):
    def __init__(self, app) -> None:
        super().__init__()
        self._app = app
        self._year: int | None = None
        self._accent = palette(app.config.theme)["accent"]
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)
        bar = QHBoxLayout()
        bar.addStretch()
        bar.addWidget(QLabel("Ano:"))
        self._year_combo = QComboBox()
        self._year_combo.currentTextChanged.connect(self._on_year)
        bar.addWidget(self._year_combo)
        outer.addLayout(bar)
        self._area, self._content, self._lay = scroll_container()
        outer.addWidget(self._area)

    def _on_year(self, text: str) -> None:
        if text.isdigit():
            self._year = int(text)
            self._render()

    def update_view(self) -> None:
        lib = self._app.library
        self._year_combo.blockSignals(True)
        self._year_combo.clear()
        if lib is None:
            self._year_combo.blockSignals(False)
            clear_layout(self._lay)
            self._lay.addWidget(empty_label("Sem fonte configurada."))
            return
        years = available_years(lib.sessions, self._app.tz)
        self._year_combo.addItems([str(y) for y in years])
        self._year_combo.blockSignals(False)
        if years:
            self._year = years[0]
            self._year_combo.setCurrentText(str(years[0]))
        self._render()

    def _render(self) -> None:
        clear_layout(self._lay)
        lib = self._app.library
        if lib is None or self._year is None:
            self._lay.addWidget(empty_label("Sem retrospectiva disponível."))
            self._lay.addStretch()
            return
        r = compute_year_review(lib.sessions, lib.games_by_id, self._year,
                                self._app.tz)
        if not r.has_data:
            self._lay.addWidget(empty_label(
                f"Não há retrospectiva para {self._year}: sem sessões válidas."))
            self._lay.addStretch()
            return

        self._lay.addWidget(self._intro(r))

        self._lay.addWidget(self._podium(r.metrics))
        top1 = r.metrics.most_played_game.label if r.metrics.most_played_game else "—"
        caption = QLabel(f"Parece que você não cansou de jogar {top1}")
        caption.setObjectName("PodiumCaption")
        caption.setAlignment(Qt.AlignHCenter)
        self._lay.addWidget(caption)

        if r.coverage.partial:
            cov = QLabel("Retrospectiva baseada no histórico parcial disponível.")
            cov.setObjectName("CardMeta")
            cov.setAlignment(Qt.AlignHCenter)
            self._lay.addWidget(cov)

        prev = self._prev_metrics(self._year)
        self._lay.addWidget(self._stats_banner(r, prev))

        radar = self._genre_card(r)
        if radar is not None:
            self._lay.addWidget(radar)

        breakdown, year_total = self._monthly_breakdown(self._year)
        self._lay.addWidget(MonthlyStackedChart(breakdown, year_total,
                                                lib.games_by_id))

        cols = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(self._kicker("Top jogos do ano"))
        left.addWidget(ranking_list(r.metrics.top_games, limit=10))
        right = QVBoxLayout()
        right.addWidget(self._kicker("Plataformas do ano"))
        right.addWidget(ranking_list(r.metrics.platform_distribution, limit=10))
        lw, rw = QWidget(), QWidget()
        lw.setLayout(left); rw.setLayout(right)
        cols.addWidget(lw, 1); cols.addWidget(rw, 1)
        self._lay.addLayout(cols)

        self._lay.addWidget(self._kicker(
            f"Explore os jogos que {self._player_name()} jogou neste ano"))
        self._lay.addWidget(self._explore_grid(r))

        streak = self._streak_card(r)
        if streak is not None:
            self._lay.addWidget(streak)
        self._lay.addStretch()

    def _kicker(self, text: str, center: bool = False) -> QWidget:
        """Rótulo editorial: barra de acento + texto maiúsculo espaçado."""
        host = QWidget()
        h = QHBoxLayout(host)
        h.setContentsMargins(0, 8, 0, 0)
        h.setSpacing(9)
        if center:
            h.addStretch()
        bar = QFrame()
        bar.setFixedSize(3, 15)
        bar.setStyleSheet(f"background: {self._accent}; border-radius: 2px;")
        lab = QLabel(text.upper())
        lab.setObjectName("KickerText")
        f = QFont(lab.font())
        f.setPointSize(10)
        f.setBold(True)
        try:
            f.setLetterSpacing(QFont.AbsoluteSpacing, 1.8)
        except Exception:
            pass
        lab.setFont(f)
        h.addWidget(bar)
        h.addWidget(lab)
        h.addStretch()
        return host

    def _player_name(self) -> str:
        try:
            name = getpass.getuser().strip()
        except Exception:
            name = ""
        return name[:1].upper() + name[1:] if name else "Jogador"

    def _intro(self, r: YearReview) -> QWidget:
        host = QFrame()
        host.setObjectName("RetroCard")
        v = QVBoxLayout(host)
        v.setContentsMargins(22, 18, 22, 20)
        v.setSpacing(4)
        v.addWidget(self._kicker(f"Retrospectiva de {self._player_name()}"))

        row = QHBoxLayout()
        row.setSpacing(14)
        year = QLabel(str(r.year))
        year.setObjectName("RetroYear")
        row.addWidget(year, 0, Qt.AlignVCenter)
        texts = QVBoxLayout()
        texts.setSpacing(2)
        hero = QLabel(f"O seu ano em jogos, {self._player_name()}")
        hero.setObjectName("RetroHero")
        hero.setWordWrap(True)
        sub = QLabel(f"No total, você passou {format_duration(r.metrics.total_seconds)} "
                     f"jogando. Bora rever o que rolou.")
        sub.setObjectName("PageSubtitle")
        sub.setWordWrap(True)
        texts.addWidget(hero)
        texts.addWidget(sub)
        row.addLayout(texts, 1)
        v.addLayout(row)
        return host

    # --------------------------------------------------------- podium
    def _podium(self, metrics: Metrics) -> QWidget:
        lib = self._app.library
        top = metrics.top_games[:3]
        # ordem visual: 2º à esquerda, 1º ao centro, 3º à direita
        slots = []
        if len(top) >= 2:
            slots.append((2, top[1]))
        if len(top) >= 1:
            slots.append((1, top[0]))
        if len(top) >= 3:
            slots.append((3, top[2]))

        host = QWidget()
        row = QHBoxLayout(host)
        row.setSpacing(18)
        row.setAlignment(Qt.AlignHCenter | Qt.AlignBottom)
        row.addStretch()
        for rank, ranked in slots:
            center = rank == 1
            w, h = (156, 232) if center else (122, 182)
            g = lib.games_by_id.get(ranked.key)
            card = QFrame()
            card.setObjectName("PodiumWinner" if center else "Card")
            v = QVBoxLayout(card)
            v.setContentsMargins(12, 12, 12, 12)
            v.setSpacing(6)
            rk = QLabel("★ CAMPEÃO" if center else f"Nº {rank}")
            rk.setObjectName("KickerText" if center else "PodiumRank")
            rk.setAlignment(Qt.AlignHCenter)
            v.addWidget(rk)
            v.addWidget(cover_fit_label(g.cover_path if g else None,
                                        ranked.label, w), 0, Qt.AlignHCenter)
            name = QLabel(ranked.label)
            name.setObjectName("CardTitle" if center else "CardMeta")
            name.setWordWrap(True)
            name.setAlignment(Qt.AlignHCenter)
            name.setFixedWidth(w)
            v.addWidget(name)
            meta = QLabel(f"{format_duration(ranked.seconds)} · {ranked.sessions} sess.")
            meta.setObjectName("CardMeta")
            meta.setAlignment(Qt.AlignHCenter)
            v.addWidget(meta)
            row.addWidget(card, 0, Qt.AlignBottom)
        row.addStretch()
        return host

    def _prev_metrics(self, year: int):
        lib = self._app.library
        prev = compute_year_review(lib.sessions, lib.games_by_id, year - 1,
                                   self._app.tz)
        return prev.metrics if prev.has_data else None

    def _delta_widget(self, cur: int, prev: int | None, year: int) -> QLabel:
        if prev is None:
            lab = QLabel("sem base comparável")
            lab.setObjectName("CardMeta")
            return lab
        diff = cur - prev
        if diff > 0:
            lab = QLabel(f"▲ {diff} a mais que em {year - 1}")
            lab.setObjectName("DeltaUp")
        elif diff < 0:
            lab = QLabel(f"▼ {abs(diff)} a menos que em {year - 1}")
            lab.setObjectName("DeltaDown")
        else:
            lab = QLabel(f"igual a {year - 1}")
            lab.setObjectName("CardMeta")
        return lab

    def _stat_group(self, value: str, label: str, delta: QLabel | None,
                    sub: str) -> QWidget:
        host = QWidget()
        v = QVBoxLayout(host)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(1)
        num = QLabel(value)
        num.setObjectName("BannerNum")
        v.addWidget(num)
        lab = QLabel(label)
        lab.setObjectName("CardTitle")
        v.addWidget(lab)
        if delta is not None:
            v.addWidget(delta)
        s = QLabel(sub)
        s.setObjectName("CardMeta")
        s.setWordWrap(True)
        v.addWidget(s)
        v.addStretch()
        return host

    def _stats_banner(self, r: YearReview, prev) -> QWidget:
        m = r.metrics
        card = QFrame()
        card.setObjectName("RetroCard")
        row = QHBoxLayout(card)
        row.setContentsMargins(20, 16, 20, 16)
        row.setSpacing(26)
        row.addWidget(self._stat_group(
            str(m.games_played), "Jogos jogados",
            self._delta_widget(m.games_played, prev.games_played if prev else None, r.year),
            f"Novos no ano: {r.new_games} · Plataformas: {m.platforms_played}"), 1)
        row.addWidget(self._stat_group(
            str(m.session_count), "Sessões",
            self._delta_widget(m.session_count, prev.session_count if prev else None, r.year),
            f"{format_duration(m.total_seconds)} · maior sequência de {m.longest_streak} dias"), 1)
        row.addWidget(self._stat_group(
            f"{r.day_fraction * 100:.0f}%", "Do tempo de dia",
            None,
            f"{r.night_fraction * 100:.0f}% de noite · média de "
            f"{format_duration(m.avg_session_seconds or 0)}/sessão"), 1)
        return card

    def _explore_grid(self, r: YearReview) -> QWidget:
        lib = self._app.library
        total = r.metrics.total_seconds or 1.0
        items: list[dict] = []
        for ranked in r.metrics.top_games[:100]:
            g = lib.games_by_id.get(ranked.key)
            pct = ranked.seconds / total * 100
            pct_txt = "< 1%" if 0 < pct < 1 else f"{pct:.0f}%"
            first = (g.first_played_at.astimezone(self._app.tz).year == r.year
                     if (g and g.first_played_at) else False)
            items.append({
                "cover": g.cover_path if g else None,
                "title": ranked.label,
                "info": f"{pct_txt} · {ranked.sessions}×",
                "first": first,
            })
        host = QFrame()
        host.setObjectName("RetroCard")
        outer = QVBoxLayout(host)
        outer.setContentsMargins(16, 14, 16, 16)
        outer.addWidget(ExploreGrid(items))
        return host

    def _monthly_breakdown(self, year: int) -> tuple[dict[int, dict[int, float]], float]:
        """Tempo por (mês, jogo) no ano e total anual, para o gráfico empilhado."""
        lib = self._app.library
        bd: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
        for s in lib.sessions:
            if not s.is_valid:
                continue
            for (yy, mm), secs in split_by_month(s, self._app.tz).items():
                if yy == year:
                    bd[mm][s.game_id] += secs
        total = sum(sum(g.values()) for g in bd.values())
        return {m: dict(g) for m, g in bd.items()}, total

    # ------------------------------------------------------- genre radar
    def _genre_distribution(self, metrics: Metrics) -> list[tuple[str, float]]:
        lib = self._app.library
        secs: dict[str, float] = defaultdict(float)
        for r in metrics.top_games:
            g = lib.games_by_id.get(r.key)
            if g and g.metadata and g.metadata.genre:
                secs[_primary_genre(g.metadata.genre)] += r.seconds
        return sorted(secs.items(), key=lambda kv: kv[1], reverse=True)[:7]

    def _genre_card(self, r: YearReview) -> QWidget | None:
        data = self._genre_distribution(r.metrics)
        if len(data) < 3:
            return None
        card = QFrame()
        card.setObjectName("RadarCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(2)
        title = QLabel("Você é o que você joga")
        title.setObjectName("SectionTitle")
        title.setAlignment(Qt.AlignHCenter)
        sub = QLabel("Este gráfico de teia ilustra os tipos de jogos em que você "
                     f"passou mais tempo em {r.year}.")
        sub.setObjectName("CardMeta")
        sub.setAlignment(Qt.AlignHCenter)
        sub.setWordWrap(True)
        lay.addWidget(title)
        lay.addWidget(sub)
        lay.addWidget(RadarChart(data))
        return card

    # -------------------------------------------------------- streak card
    def _streak_games(self, rng: tuple[date, date]):
        lib = self._app.library
        start, end = rng
        seen: set[int] = set()
        games = []
        for s in lib.sessions:
            if not s.is_valid:
                continue
            for d in split_by_day(s, self._app.tz):
                if start <= d <= end and s.game_id not in seen:
                    seen.add(s.game_id)
                    g = lib.games_by_id.get(s.game_id)
                    if g:
                        games.append(g)
        games.sort(key=lambda g: g.total_seconds, reverse=True)
        return games

    def _streak_card(self, r: YearReview) -> QWidget | None:
        if r.metrics.longest_streak < 1 or not r.longest_streak_range:
            return None
        start, end = r.longest_streak_range
        card = QFrame()
        card.setObjectName("StreakCard")
        v = QVBoxLayout(card)
        v.setContentsMargins(22, 18, 22, 18)
        v.setSpacing(10)
        title = QLabel(f"Sua maior sequência diária: {r.metrics.longest_streak}")
        title.setObjectName("SectionTitle")
        title.setAlignment(Qt.AlignHCenter)
        v.addWidget(title)

        tl = QHBoxLayout()
        tl.addWidget(QLabel(f"{start.day} de {_MONTHS_FULL[start.month]}"))
        line = QFrame()
        line.setFixedHeight(2)
        line.setStyleSheet("background: #6B7280;")
        tl.addWidget(line, 1)
        end_lab = QLabel(f"{end.day} de {_MONTHS_FULL[end.month]}")
        end_lab.setAlignment(Qt.AlignRight)
        tl.addWidget(end_lab)
        v.addLayout(tl)

        games = self._streak_games(r.longest_streak_range)
        if games:
            cap = QLabel(f"Durante esse tempo, você jogou {len(games)} jogos "
                         f"diferentes:")
            cap.setObjectName("CardMeta")
            cap.setAlignment(Qt.AlignHCenter)
            v.addWidget(cap)
            covers = QHBoxLayout()
            covers.setSpacing(8)
            covers.addStretch()
            for g in games[:12]:
                covers.addWidget(cover_fit_label(g.cover_path, g.display_title, 56))
            covers.addStretch()
            holder = QWidget()
            holder.setLayout(covers)
            v.addWidget(holder)
        return card

    # ------------------------------------------------------------ charts
    def _monthly_chart(self, monthly: dict[int, float]) -> QFrame:
        box = QFrame()
        box.setObjectName("Tile")
        box.setMinimumHeight(185)
        lay = QHBoxLayout(box)
        lay.setContentsMargins(16, 16, 16, 10)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignBottom)
        maximum = max(monthly.values()) or 1
        for m in range(1, 13):
            secs = monthly.get(m, 0.0)
            col = QVBoxLayout()
            col.setAlignment(Qt.AlignBottom)
            bar = QFrame()
            bar.setObjectName("BarFill")
            bar.setFixedHeight(max(3, int(130 * secs / maximum)))
            bar.setToolTip(f"{_MONTHS[m-1]}: {format_duration(secs)}")
            lab = QLabel(_MONTHS[m - 1])
            lab.setObjectName("TileLabel")
            lab.setAlignment(Qt.AlignHCenter)
            col.addWidget(bar)
            col.addWidget(lab)
            wrap = QWidget()
            wrap.setLayout(col)
            lay.addWidget(wrap, 1)
        return box

    _bucket_colors = _HEAT

    def _bucket(self, secs: float, maximum: float) -> int:
        if secs <= 0:
            return 0
        if maximum <= 0:
            return 1
        return min(4, 1 + int((secs / maximum) * 3.999))

    def _calendar(self, year: int, days: dict[date, float]) -> QFrame:
        box = QFrame()
        box.setObjectName("Tile")
        root = QVBoxLayout(box)
        root.setContentsMargins(16, 14, 16, 14)
        grid_host = QWidget()
        grid = QGridLayout(grid_host)
        grid.setSpacing(2)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        maximum = max(days.values()) if days else 0.0
        start = date(year, 1, 1)
        end = date(year, 12, 31)
        base_col = start.weekday()
        cur = start
        while cur <= end:
            col = ((cur - start).days + base_col) // 7
            row = cur.weekday()
            secs = days.get(cur, 0.0)
            cell = QFrame()
            cell.setFixedSize(11, 11)
            cell.setStyleSheet(
                f"background: {_HEAT[self._bucket(secs, maximum)]};"
                " border-radius: 2px;")
            cell.setToolTip(
                f"{cur.strftime('%d/%m/%Y')}: {format_duration(secs)}" if secs > 0
                else f"{cur.strftime('%d/%m/%Y')}: sem atividade registrada")
            grid.addWidget(cell, row, col)
            cur += timedelta(days=1)
        root.addWidget(grid_host)
        legend = QLabel("menos  ▪ ▪ ▪ ▪ ▪  mais")
        legend.setObjectName("CardMeta")
        root.addWidget(legend)
        return box

    def _hourly(self, hourly: dict[int, float]) -> QFrame:
        box = QFrame()
        box.setObjectName("Tile")
        box.setMinimumHeight(150)
        lay = QHBoxLayout(box)
        lay.setContentsMargins(16, 14, 16, 8)
        lay.setSpacing(3)
        lay.setAlignment(Qt.AlignBottom)
        maximum = max(hourly.values()) or 1
        for hour in range(24):
            secs = hourly.get(hour, 0.0)
            col = QVBoxLayout()
            col.setAlignment(Qt.AlignBottom)
            bar = QFrame()
            bar.setObjectName("BarFill")
            bar.setFixedHeight(max(2, int(100 * secs / maximum)))
            bar.setToolTip(f"{hour:02d}h: {format_duration(secs)}")
            lab = QLabel(f"{hour:02d}")
            lab.setObjectName("TileLabel")
            lab.setAlignment(Qt.AlignHCenter)
            col.addWidget(bar)
            col.addWidget(lab)
            wrap = QWidget()
            wrap.setLayout(col)
            lay.addWidget(wrap, 1)
        return box
