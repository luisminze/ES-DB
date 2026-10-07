from datetime import datetime, timezone, timedelta

from esdb.domain.models import DurationKind, Game, Session
from esdb.domain.year_review import compute_year_review, available_years

TZ = timezone(timedelta(hours=-3))
NOW = datetime(2027, 1, 15, tzinfo=TZ)


def mk(start, end, dur, kind=DurationKind.NORMAL, sid=1, gid=1):
    return Session(sid, gid, datetime.fromisoformat(start),
                   datetime.fromisoformat(end), dur, kind)


def test_cross_year_session_counted_in_both_years_fractions():
    # 2026-12-31 23:00 -> 2027-01-01 01:00 (7200s)
    s = mk("2026-12-31T23:00:00-03:00", "2027-01-01T01:00:00-03:00", 7200)
    games = {1: Game(1, "A", "PS2")}
    r2026 = compute_year_review([s], games, 2026, TZ, now=NOW)
    r2027 = compute_year_review([s], games, 2027, TZ, now=NOW)
    assert abs(r2026.metrics.total_seconds - 3600) < 5
    assert abs(r2027.metrics.total_seconds - 3600) < 5


def test_monthly_sum_equals_total_invariant():
    games = {1: Game(1, "A", "PS2"), 2: Game(2, "B", "X360")}
    sessions = [
        mk("2026-03-10T10:00:00-03:00", "2026-03-10T11:00:00-03:00", 3600, sid=1, gid=1),
        mk("2026-07-20T20:00:00-03:00", "2026-07-20T22:30:00-03:00", 9000, sid=2, gid=2),
        mk("2026-07-21T23:30:00-03:00", "2026-07-22T00:30:00-03:00", 3600, sid=3, gid=1),
    ]
    r = compute_year_review(sessions, games, 2026, TZ, now=NOW)
    assert abs(sum(r.monthly_activity.values()) - r.metrics.total_seconds) < 1.0
    assert abs(sum(r.calendar_days.values()) - r.metrics.total_seconds) < 1.0


def test_empty_year_has_no_data():
    games = {1: Game(1, "A", "PS2")}
    s = mk("2020-05-01T12:00:00-03:00", "2020-05-01T13:00:00-03:00", 3600)
    r = compute_year_review([s], games, 2026, TZ, now=NOW)
    assert not r.has_data
    assert r.metrics.total_seconds == 0.0


def test_available_years():
    s = mk("2026-12-31T23:00:00-03:00", "2027-01-01T01:00:00-03:00", 7200)
    assert available_years([s], TZ) == [2027, 2026]
