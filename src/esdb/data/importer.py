"""Classificação e importação de sessões (MAIN.md §8, RF-02, RF-09).

``classify_session`` é uma função pura, testável, que decide o ``DurationKind``
de uma sessão a partir dos textos de horário e da duração persistida.
"""

from __future__ import annotations

from datetime import datetime, timedelta, tzinfo

from ..domain.models import DurationKind, Session
from ..domain.timeparse import parse_timestamp
from .source_adapter import SourceSession

MISMATCH_TOLERANCE = 1  # segundo (MAIN.md §8)


def classify_session(src: SourceSession, tz: tzinfo) -> Session:
    """Transforma uma sessão da fonte em ``Session`` de domínio classificada."""
    start = parse_timestamp(src.start_time, assume_tz=tz)
    end = parse_timestamp(src.end_time, assume_tz=tz)

    if start is None or end is None:
        anchor = start or end or datetime.now(tz)
        return Session(src.id, src.game_id, anchor, anchor,
                       max(0, src.duration), DurationKind.INVALID_TIMESTAMP)

    if src.duration < 0:
        return Session(src.id, src.game_id, start, end, src.duration,
                       DurationKind.NEGATIVE_DURATION)

    if src.duration == 0:
        return Session(src.id, src.game_id, start, end, 0,
                       DurationKind.QUICK_LAUNCH)

    wall = (end - start).total_seconds()
    if wall < 0:
        return Session(src.id, src.game_id, start, end, src.duration,
                       DurationKind.INVALID_TIMESTAMP)
    if abs(wall - src.duration) > MISMATCH_TOLERANCE:
        return Session(src.id, src.game_id, start, end, src.duration,
                       DurationKind.DURATION_MISMATCH)

    return Session(src.id, src.game_id, start, end, src.duration,
                   DurationKind.NORMAL)
