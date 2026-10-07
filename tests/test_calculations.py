from datetime import datetime, timezone, timedelta

from esdb.domain.calculations import (Period, compute_metrics, format_duration,
                                      seconds_in_period, split_by_day)
from esdb.domain.models import DurationKind, Game, Session

TZ = timezone(timedelta(hours=-3))


def mk(start, end, dur, kind=DurationKind.NORMAL, sid=1, gid=1):
    return Session(sid, gid, datetime.fromisoformat(start),
                   datetime.fromisoformat(end), dur, kind)


def test_split_across_midnight_preserves_seconds():
    # 23:00 -> 01:00 (7200s), cruza a meia-noite
    s = mk("2026-10-06T23:00:00-03:00", "2026-10-07T01:00:00-03:00", 7200)
    parts = split_by_day(s, TZ)
    assert len(parts) == 2
    assert abs(sum(parts.values()) - 7200) < 1e-6
    # metade em cada dia
    assert abs(parts[datetime(2026, 10, 6).date()] - 3600) < 1.0


def test_quick_launch_excluded_from_time():
    s = mk("2026-10-06T12:00:00-03:00", "2026-10-06T12:00:00-03:00", 0,
           DurationKind.QUICK_LAUNCH)
    assert split_by_day(s, TZ) == {}
    assert seconds_in_period(s, Period(), TZ) == 0.0


def test_metrics_counts_and_time():
    games = {1: Game(1, "A", "PS2"), 2: Game(2, "B", "PS2")}
    sessions = [
        mk("2026-10-06T12:00:00-03:00", "2026-10-06T13:00:00-03:00", 3600, gid=1, sid=1),
        mk("2026-10-06T14:00:00-03:00", "2026-10-06T14:30:00-03:00", 1800, gid=2, sid=2),
        mk("2026-10-06T15:00:00-03:00", "2026-10-06T15:00:00-03:00", 0,
           DurationKind.QUICK_LAUNCH, gid=1, sid=3),
    ]
    m = compute_metrics(sessions, games, Period(), TZ)
    assert m.total_seconds == 5400
    assert m.session_count == 3          # inclui o início rápido
    assert m.quick_launches == 1
    assert m.games_played == 2
    assert m.most_played_game.key == 1   # 3600 > 1800


def test_longest_streak():
    games = {1: Game(1, "A", "PS2")}
    sessions = [
        mk("2026-10-01T12:00:00-03:00", "2026-10-01T12:30:00-03:00", 1800, sid=1),
        mk("2026-10-02T12:00:00-03:00", "2026-10-02T12:30:00-03:00", 1800, sid=2),
        mk("2026-10-03T12:00:00-03:00", "2026-10-03T12:30:00-03:00", 1800, sid=3),
        mk("2026-10-10T12:00:00-03:00", "2026-10-10T12:30:00-03:00", 1800, sid=4),
    ]
    m = compute_metrics(sessions, games, Period(), TZ)
    assert m.longest_streak == 3


def test_period_filters_out_of_range():
    games = {1: Game(1, "A", "PS2")}
    sessions = [mk("2026-01-01T12:00:00-03:00", "2026-01-01T13:00:00-03:00", 3600)]
    period = Period(datetime(2026, 6, 1, tzinfo=TZ), datetime(2026, 7, 1, tzinfo=TZ))
    m = compute_metrics(sessions, games, period, TZ)
    assert m.total_seconds == 0.0


def test_format_duration():
    assert format_duration(0) == "—"
    assert format_duration(90) == "1min"
    assert format_duration(3660) == "1h 01min"
    assert format_duration(7200) == "2h"
