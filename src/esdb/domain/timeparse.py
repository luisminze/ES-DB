"""Parsing de timestamps da fonte e utilidades de fuso.

A fonte grava ``%Y-%m-%dT%H:%M:%S%z`` com offset sem dois-pontos (``-0300``).
``datetime.strptime`` com ``%z`` aceita esse formato (MAIN.md RNF-09).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo

_FORMATS = (
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S",      # sem offset (assume fuso do usuário ao converter)
)


def parse_timestamp(value: str, assume_tz: tzinfo | None = None) -> datetime | None:
    """Converte o texto da fonte em ``datetime`` ciente de fuso.

    Retorna ``None`` quando o valor não é parseável — o chamador marca a sessão
    como ``invalid_timestamp`` (nunca inventa um horário).
    """
    if not value:
        return None
    text = value.strip()
    for fmt in _FORMATS:
        try:
            dt = datetime.strptime(text, fmt)
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=assume_tz or timezone.utc)
        return dt
    return None


def to_local(dt: datetime, tz: tzinfo) -> datetime:
    """Converte para o fuso escolhido pelo usuário antes de determinar o dia."""
    return dt.astimezone(tz)


def day_start(dt: datetime) -> datetime:
    """Meia-noite local do dia de ``dt`` (``dt`` já no fuso do usuário)."""
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def next_day(dt: datetime) -> datetime:
    return day_start(dt) + timedelta(days=1)


def local_offset() -> timezone:
    """Fuso local do computador, como fallback de configuração."""
    off = datetime.now().astimezone().utcoffset() or timedelta(0)
    return timezone(off)
