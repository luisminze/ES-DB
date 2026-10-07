"""Regras de cálculo do ES-DB (MAIN.md §8).

Princípios:
- O tempo jogado vem de ``duration_seconds`` de sessões **normais válidas**,
  distribuído proporcionalmente à interseção com o período/baldes temporais.
- Sessões que cruzam meia-noite/hora/mês são fracionadas sem perder nem duplicar
  segundos (invariante verificada em testes).
- Sessões de duração zero (inícios rápidos) só contam no total de sessões.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, tzinfo
from typing import Callable, Iterable, Mapping

from .models import DurationKind, Game, Session
from .timeparse import day_start, next_day


@dataclass(slots=True)
class Period:
    """Intervalo semiaberto ``[start, end)`` no fuso do usuário.

    ``start``/``end`` ``None`` significam "sem limite" (todo o histórico).
    """

    start: datetime | None = None
    end: datetime | None = None
    label: str = "Todo o histórico"

    def contains(self, dt: datetime) -> bool:
        if self.start and dt < self.start:
            return False
        if self.end and dt >= self.end:
            return False
        return True


# --------------------------------------------------------------------------- #
# Fracionamento temporal
# --------------------------------------------------------------------------- #

def _first_of_next_month(dt: datetime) -> datetime:
    year, month = dt.year, dt.month
    if month == 12:
        return dt.replace(year=year + 1, month=1, day=1, hour=0, minute=0,
                          second=0, microsecond=0)
    return dt.replace(month=month + 1, day=1, hour=0, minute=0, second=0,
                      microsecond=0)


def _next_hour(dt: datetime) -> datetime:
    return dt.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)


def _bucketize(
    session: Session,
    tz: tzinfo,
    key: Callable[[datetime], object],
    boundary_next: Callable[[datetime], datetime],
) -> dict[object, float]:
    """Distribui ``duration_seconds`` entre baldes, proporcional ao tempo de
    relógio em cada balde. Não perde nem duplica segundos."""
    if not session.is_valid:
        return {}
    start = session.started_at.astimezone(tz)
    end = session.ended_at.astimezone(tz)
    total = (end - start).total_seconds()
    if total <= 0:
        return {key(start): float(session.duration_seconds)}
    out: dict[object, float] = defaultdict(float)
    cursor = start
    while cursor < end:
        nxt = min(boundary_next(cursor), end)
        seg = (nxt - cursor).total_seconds()
        out[key(cursor)] += session.duration_seconds * seg / total
        cursor = nxt
    return dict(out)


def split_by_day(session: Session, tz: tzinfo) -> dict[date, float]:
    return _bucketize(session, tz, lambda d: d.date(), next_day)  # type: ignore[arg-type]


def split_by_hour(session: Session, tz: tzinfo) -> dict[int, float]:
    return _bucketize(session, tz, lambda d: d.hour, _next_hour)  # type: ignore[return-value]


def split_by_month(session: Session, tz: tzinfo) -> dict[tuple[int, int], float]:
    return _bucketize(session, tz, lambda d: (d.year, d.month), _first_of_next_month)  # type: ignore[return-value]


def seconds_in_period(session: Session, period: Period, tz: tzinfo) -> float:
    """Segundos jogados de ``session`` dentro de ``period`` (proporcional)."""
    if not session.is_valid:
        return 0.0
    start = session.started_at.astimezone(tz)
    end = session.ended_at.astimezone(tz)
    total = (end - start).total_seconds()
    if total <= 0:
        return float(session.duration_seconds) if period.contains(start) else 0.0
    lo = max(start, period.start) if period.start else start
    hi = min(end, period.end) if period.end else end
    if hi <= lo:
        return 0.0
    return session.duration_seconds * (hi - lo).total_seconds() / total


def overlaps(session: Session, period: Period, tz: tzinfo) -> bool:
    start = session.started_at.astimezone(tz)
    end = session.ended_at.astimezone(tz)
    if period.start and end < period.start:
        return False
    if period.end and start >= period.end:
        return False
    return True


# --------------------------------------------------------------------------- #
# Métricas agregadas
# --------------------------------------------------------------------------- #

@dataclass(slots=True)
class Ranked:
    key: object
    label: str
    seconds: float
    sessions: int


@dataclass(slots=True)
class Metrics:
    total_seconds: float = 0.0
    session_count: int = 0
    quick_launches: int = 0
    games_played: int = 0
    platforms_played: int = 0
    avg_session_seconds: float | None = None
    most_played_game: Ranked | None = None
    most_played_platform: Ranked | None = None
    most_active_day: tuple[date, float] | None = None
    longest_streak: int = 0
    last_session_at: datetime | None = None
    daily_activity: dict[date, float] = field(default_factory=dict)
    platform_distribution: list[Ranked] = field(default_factory=list)
    top_games: list[Ranked] = field(default_factory=list)


def _longest_streak(days: Iterable[date]) -> int:
    ordered = sorted(set(days))
    if not ordered:
        return 0
    best = run = 1
    for prev, cur in zip(ordered, ordered[1:]):
        if cur - prev == timedelta(days=1):
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best


def compute_metrics(
    sessions: Iterable[Session],
    games_by_id: Mapping[int, Game],
    period: Period,
    tz: tzinfo,
) -> Metrics:
    """Calcula todas as métricas do painel/estatísticas para o período."""
    m = Metrics()
    game_seconds: dict[int, float] = defaultdict(float)
    game_sessions: dict[int, int] = defaultdict(int)
    platform_seconds: dict[str, float] = defaultdict(float)
    platform_sessions: dict[str, int] = defaultdict(int)
    valid_session_count = 0
    active_days: set[date] = set()

    for s in sessions:
        if not overlaps(s, period, tz):
            continue
        if s.kind.counts_as_session:
            m.session_count += 1
        if s.kind is DurationKind.QUICK_LAUNCH:
            m.quick_launches += 1
        if not s.is_valid:
            continue
        secs = seconds_in_period(s, period, tz)
        if secs <= 0:
            continue
        valid_session_count += 1
        game = games_by_id.get(s.game_id)
        game_seconds[s.game_id] += secs
        game_sessions[s.game_id] += 1
        if game:
            platform_seconds[game.platform] += secs
            platform_sessions[game.platform] += 1
        m.total_seconds += secs
        end_local = s.ended_at.astimezone(tz)
        if m.last_session_at is None or end_local > m.last_session_at:
            m.last_session_at = end_local
        for d, ds in split_by_day(s, tz).items():
            if _day_in_period(d, period, tz):
                m.daily_activity[d] = m.daily_activity.get(d, 0.0) + ds
                active_days.add(d)

    m.games_played = sum(1 for v in game_seconds.values() if v > 0)
    m.platforms_played = sum(1 for v in platform_seconds.values() if v > 0)
    if valid_session_count:
        m.avg_session_seconds = m.total_seconds / valid_session_count
    m.longest_streak = _longest_streak(active_days)

    if game_seconds:
        gid = max(game_seconds, key=lambda k: (game_seconds[k], game_sessions[k]))
        g = games_by_id.get(gid)
        m.most_played_game = Ranked(gid, g.display_title if g else str(gid),
                                    game_seconds[gid], game_sessions[gid])
    if platform_seconds:
        plat = max(platform_seconds, key=lambda k: platform_seconds[k])
        m.most_played_platform = Ranked(plat, plat, platform_seconds[plat],
                                        platform_sessions[plat])
    if m.daily_activity:
        day = max(m.daily_activity, key=lambda k: (m.daily_activity[k], k))
        m.most_active_day = (day, m.daily_activity[day])

    m.platform_distribution = sorted(
        (Ranked(p, p, sec, platform_sessions[p]) for p, sec in platform_seconds.items()),
        key=lambda r: r.seconds, reverse=True)
    m.top_games = sorted(
        (Ranked(gid, (games_by_id[gid].display_title if gid in games_by_id else str(gid)),
                sec, game_sessions[gid]) for gid, sec in game_seconds.items()),
        key=lambda r: (r.seconds, r.sessions), reverse=True)
    return m


def _day_in_period(d: date, period: Period, tz: tzinfo) -> bool:
    start = datetime.combine(d, datetime.min.time(), tzinfo=tz)
    end = start + timedelta(days=1)
    if period.start and end <= period.start:
        return False
    if period.end and start >= period.end:
        return False
    return True


def format_duration(seconds: float) -> str:
    """Formata segundos como ``Xh YYmin`` / ``YYmin`` / ``—``."""
    secs = int(round(seconds))
    if secs <= 0:
        return "—"
    hours, rem = divmod(secs, 3600)
    minutes = rem // 60
    if hours:
        return f"{hours}h {minutes:02d}min" if minutes else f"{hours}h"
    if minutes:
        return f"{minutes}min"
    return f"{secs}s"
