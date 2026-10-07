from datetime import timezone, timedelta

from esdb.data.importer import classify_session
from esdb.data.source_adapter import SourceSession
from esdb.domain.models import DurationKind

TZ = timezone(timedelta(hours=-3))


def src(start, end, duration, sid=1, gid=1):
    return SourceSession(sid, gid, start, end, duration)


def test_normal():
    s = classify_session(src("2026-10-06T12:00:00-0300",
                             "2026-10-06T12:10:00-0300", 600), TZ)
    assert s.kind is DurationKind.NORMAL and s.is_valid


def test_quick_launch():
    s = classify_session(src("2026-10-06T12:00:00-0300",
                             "2026-10-06T12:00:00-0300", 0), TZ)
    assert s.kind is DurationKind.QUICK_LAUNCH
    assert not s.is_valid and s.kind.counts_as_session


def test_negative():
    s = classify_session(src("2026-10-06T12:00:00-0300",
                             "2026-10-06T12:10:00-0300", -5), TZ)
    assert s.kind is DurationKind.NEGATIVE_DURATION and not s.is_valid


def test_mismatch_beyond_tolerance():
    s = classify_session(src("2026-10-06T12:00:00-0300",
                             "2026-10-06T12:10:00-0300", 999), TZ)
    assert s.kind is DurationKind.DURATION_MISMATCH


def test_one_second_tolerance_is_normal():
    s = classify_session(src("2026-10-06T12:00:00-0300",
                             "2026-10-06T12:10:00-0300", 601), TZ)
    assert s.kind is DurationKind.NORMAL


def test_invalid_timestamp():
    s = classify_session(src("garbage", "2026-10-06T12:10:00-0300", 600), TZ)
    assert s.kind is DurationKind.INVALID_TIMESTAMP and not s.is_valid
