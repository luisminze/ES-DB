"""Construtores de períodos predefinidos (MAIN.md RF-04)."""

from __future__ import annotations

from datetime import datetime, timedelta, tzinfo

from .calculations import Period, _first_of_next_month
from .timeparse import day_start

PRESETS = [
    ("last7", "Últimos 7 dias"),
    ("last30", "Últimos 30 dias"),
    ("month", "Mês atual"),
    ("year", "Ano atual"),
    ("all", "Todo o histórico"),
]


def build_period(kind: str, tz: tzinfo, now: datetime | None = None) -> Period:
    now = (now or datetime.now(tz)).astimezone(tz)
    today = day_start(now)
    tomorrow = today + timedelta(days=1)
    if kind == "last7":
        return Period(tomorrow - timedelta(days=7), tomorrow, "Últimos 7 dias")
    if kind == "last30":
        return Period(tomorrow - timedelta(days=30), tomorrow, "Últimos 30 dias")
    if kind == "month":
        start = today.replace(day=1)
        return Period(start, _first_of_next_month(start), "Mês atual")
    if kind == "year":
        start = today.replace(month=1, day=1)
        return Period(start, start.replace(year=start.year + 1), "Ano atual")
    return Period(None, None, "Todo o histórico")


def year_period(year: int, tz: tzinfo) -> Period:
    start = datetime(year, 1, 1, tzinfo=tz)
    end = datetime(year + 1, 1, 1, tzinfo=tz)
    return Period(start, end, str(year))
