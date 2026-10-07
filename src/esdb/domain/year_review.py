"""Retrospectiva anual (RETROSPECTIVA.md).

Gera um ``YearReview`` em memória a partir das sessões normais válidas que
interceptam o ano, com fracionamento temporal sem perdas (critério de invariância
em testes).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, tzinfo
from typing import Iterable, Mapping

from . import calculations as calc
from .calculations import Metrics, Period, Ranked
from .models import Game, Session
from .periods import year_period


@dataclass(slots=True)
class CoverageStatus:
    status: str
    observed_first: datetime | None
    observed_last: datetime | None
    partial: bool


@dataclass(slots=True)
class YearReview:
    year: int
    generated_at: datetime
    timezone_name: str
    calculation_version: int
    coverage: CoverageStatus
    metrics: Metrics
    monthly_activity: dict[int, float]          # 1..12 -> segundos
    hourly_activity: dict[int, float]            # 0..23 -> segundos
    calendar_days: dict[date, float]             # dia -> segundos
    day_fraction: float                          # fração 6h–18h
    night_fraction: float
    new_games: int
    longest_streak_range: tuple[date, date] | None
    has_data: bool


CALCULATION_VERSION = 1


def _coverage(year: int, first: datetime | None, last: datetime | None,
              tz: tzinfo) -> CoverageStatus:
    if first is None or last is None:
        return CoverageStatus("unknown", first, last, True)
    start = datetime(year, 1, 1, tzinfo=tz)
    end = datetime(year, 12, 31, 23, 59, 59, tzinfo=tz)
    starts_after = first > start.replace(hour=0)
    ends_before = last < end
    if not starts_after and not ends_before:
        status = "spans_full_calendar_year"
    elif starts_after and ends_before:
        status = "partial_range"
    elif starts_after:
        status = "starts_after_year_begin"
    else:
        status = "ends_before_year_end"
    return CoverageStatus(status, first, last, status != "spans_full_calendar_year")


def available_years(sessions: Iterable[Session], tz: tzinfo) -> list[int]:
    years: set[int] = set()
    for s in sessions:
        if not s.is_valid:
            continue
        years.add(s.started_at.astimezone(tz).year)
        years.add(s.ended_at.astimezone(tz).year)
    return sorted(years, reverse=True)


def compute_year_review(
    sessions: list[Session],
    games_by_id: Mapping[int, Game],
    year: int,
    tz: tzinfo,
    now: datetime | None = None,
) -> YearReview:
    now = (now or datetime.now(tz)).astimezone(tz)
    period = year_period(year, tz)
    metrics = calc.compute_metrics(sessions, games_by_id, period, tz)

    monthly: dict[int, float] = {m: 0.0 for m in range(1, 13)}
    hourly: dict[int, float] = {h: 0.0 for h in range(24)}
    calendar: dict[date, float] = {}
    observed_first: datetime | None = None
    observed_last: datetime | None = None
    first_play: dict[int, int] = {}      # game_id -> min year observed anywhere

    # Primeiro registro de cada jogo (para "novos jogos no ano")
    for s in sessions:
        if not s.is_valid:
            continue
        y = s.started_at.astimezone(tz).year
        first_play[s.game_id] = min(first_play.get(s.game_id, y), y)

    for s in sessions:
        if not s.is_valid or not calc.overlaps(s, period, tz):
            continue
        st = s.started_at.astimezone(tz)
        en = s.ended_at.astimezone(tz)
        if observed_first is None or st < observed_first:
            observed_first = st
        if observed_last is None or en > observed_last:
            observed_last = en
        for m, secs in calc.split_by_month(s, tz).items():
            if m[0] == year:
                monthly[m[1]] += secs
        for h, secs in calc.split_by_hour(s, tz).items():
            # fraciona por hora mas só conta o que cai no ano via dias
            hourly[h] += secs * _year_fraction(s, year, tz)
        for d, secs in calc.split_by_day(s, tz).items():
            if d.year == year:
                calendar[d] = calendar.get(d, 0.0) + secs

    day_secs = sum(v for h, v in hourly.items() if 6 <= h < 18)
    total_h = sum(hourly.values()) or 1.0
    new_games = sum(1 for gid, yr in first_play.items()
                    if yr == year and gid in games_by_id)

    coverage = _coverage(year, observed_first, observed_last, tz)
    return YearReview(
        year=year,
        generated_at=now,
        timezone_name=str(tz),
        calculation_version=CALCULATION_VERSION,
        coverage=coverage,
        metrics=metrics,
        monthly_activity=monthly,
        hourly_activity=hourly,
        calendar_days=calendar,
        day_fraction=day_secs / total_h,
        night_fraction=1.0 - day_secs / total_h,
        new_games=new_games,
        longest_streak_range=_streak_range(calendar),
        has_data=metrics.total_seconds > 0,
    )


def _year_fraction(session: Session, year: int, tz: tzinfo) -> float:
    """Fração da duração da sessão que cai no ano (para o histograma horário)."""
    by_day = calc.split_by_day(session, tz)
    total = sum(by_day.values()) or 1.0
    in_year = sum(v for d, v in by_day.items() if d.year == year)
    return in_year / total


def _streak_range(calendar: dict[date, float]) -> tuple[date, date] | None:
    days = sorted(d for d, v in calendar.items() if v > 0)
    if not days:
        return None
    best = (days[0], days[0])
    run_start = days[0]
    prev = days[0]
    for cur in days[1:]:
        if (cur - prev).days == 1:
            if (cur - run_start).days > (best[1] - best[0]).days:
                best = (run_start, cur)
        else:
            run_start = cur
        prev = cur
    return best
