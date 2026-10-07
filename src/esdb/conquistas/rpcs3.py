"""Parser de troféus do RPCS3 (CONQUISTAS.md §3).

Definições: ``TROPCONF.SFM`` (XML, confiável).
Progresso: ``TROPUSR.DAT`` (binário, melhor-esforço, defensivo).

Formato do TROPUSR.DAT (verificado contra arquivos reais):
- Cabeçalho 0x30: magic ``0x818F54AD`` (big-endian), em 0x08 a quantidade de tabelas.
- Tabelas (0x20 cada) a partir de 0x30: ``type, entry_size, _, count, offset(u64)``.
- A tabela ``type=6`` guarda o estado: cada registro tem 0x10 de cabeçalho +
  payload; no payload, ``word[0]``=trophy_id, ``word[1]``=desbloqueado (0/1),
  e em 0x10 um ``CellRtcTick`` (u64, microssegundos desde o ano 1) do desbloqueio.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

from .models import Achievement, GameAchievements, Grade

_RTC_EPOCH = datetime(1, 1, 1)
_GRADE = {"P": Grade.PLATINUM, "G": Grade.GOLD, "S": Grade.SILVER,
          "B": Grade.BRONZE}


def _parse_tropconf(path: Path) -> tuple[str, list[Achievement]]:
    """Lê definições do TROPCONF.SFM. Confiável; tolera comentário de assinatura."""
    try:
        tree = ET.parse(path)
    except (ET.ParseError, OSError):
        return "", []
    root = tree.getroot()
    title = (root.findtext("title-name") or "").strip()
    out: list[Achievement] = []
    base = path.parent
    for t in root.findall("trophy"):
        tid = (t.get("id") or "").strip()
        grade = _GRADE.get((t.get("ttype") or "").strip().upper(), Grade.UNKNOWN)
        hidden = (t.get("hidden") or "no").strip().lower() == "yes"
        icon = base / f"TROP{tid}.PNG"
        out.append(Achievement(
            key=tid,
            name=(t.findtext("name") or "").strip(),
            description=(t.findtext("detail") or "").strip(),
            grade=grade,
            hidden=hidden,
            icon_path=str(icon) if icon.is_file() else None,
        ))
    return title, out


def _parse_tropusr(path: Path) -> dict[int, tuple[bool, datetime | None]] | None:
    """Lê o estado de desbloqueio. Retorna ``None`` se não puder interpretar com
    segurança (o chamador então marca o jogo como progresso indisponível)."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if len(data) < 0x50:
        return None

    def be(off: int, size: int = 4) -> int:
        return int.from_bytes(data[off:off + size], "big")

    if be(0) != 0x818F54AD:
        return None
    tables = be(0x08)
    if not (0 < tables <= 16):
        return None

    target = None
    for i in range(tables):
        o = 0x30 + i * 0x20
        if o + 0x20 > len(data):
            return None
        if be(o) == 6:
            target = (be(o + 4), be(o + 0x0C), be(o + 0x10, 8))  # size, count, offset
            break
    if target is None:
        return None
    entry_size, count, offset = target
    if entry_size < 0x60 or not (0 < count <= 10000):
        return None

    stride = entry_size + 0x10  # 0x10 de cabeçalho por registro
    out: dict[int, tuple[bool, datetime | None]] = {}
    for i in range(count):
        rec = offset + i * stride
        pay = rec + 0x10
        if pay + 0x18 > len(data):
            break
        tid = be(pay)
        unlocked = be(pay + 0x04) == 1
        when: datetime | None = None
        if unlocked:
            raw = be(pay + 0x10, 8)
            try:
                cand = _RTC_EPOCH + timedelta(microseconds=raw)
                if 2000 <= cand.year <= 2100:
                    when = cand
            except (OverflowError, OSError):
                when = None
        out[tid] = (unlocked, when)
    return out or None


def scan_rpcs3(trophy_dirs: list[Path]) -> list[GameAchievements]:
    """Varre pastas de troféu do RPCS3 (``…/trophy/NPWR…`` por jogo)."""
    games: list[GameAchievements] = []
    for base in trophy_dirs:
        if not base.is_dir():
            continue
        for gdir in sorted(p for p in base.iterdir() if p.is_dir()):
            conf = gdir / "TROPCONF.SFM"
            if not conf.is_file():
                continue
            title, defs = _parse_tropconf(conf)
            if not defs:
                continue
            progress = _parse_tropusr(gdir / "TROPUSR.DAT")
            available = progress is not None
            for ach in defs:
                try:
                    tid = int(ach.key)
                except ValueError:
                    continue
                if available and tid in progress:
                    ach.unlocked, ach.unlocked_at = progress[tid]
            icon = gdir / "ICON0.PNG"
            games.append(GameAchievements(
                emulator="RPCS3",
                title=title or gdir.name,
                comm_id=gdir.name,
                source_path=str(gdir),
                achievements=defs,
                progress_available=available,
                icon_path=str(icon) if icon.is_file() else None,
            ))
    return games
