from datetime import timezone, timedelta

from esdb.domain.timeparse import parse_timestamp


def test_parses_offset_without_colon():
    dt = parse_timestamp("2026-09-24T13:09:58-0300")
    assert dt is not None
    assert dt.utcoffset() == timedelta(hours=-3)
    assert (dt.year, dt.month, dt.day, dt.hour) == (2026, 9, 24, 13)


def test_invalid_returns_none():
    assert parse_timestamp("not a date") is None
    assert parse_timestamp("") is None


def test_naive_gets_assumed_tz():
    tz = timezone(timedelta(hours=-3))
    dt = parse_timestamp("2026-01-01T00:00:00", assume_tz=tz)
    assert dt is not None and dt.utcoffset() == timedelta(hours=-3)
