"""Parser de conquistas do Xenia (arquivos ``.gpd``, formato XDBF).

O XDBF é o contêiner de perfil do Xbox 360. Namespaces usados:
1=conquista, 2=imagem (PNG), 4=título jogado (``TitlePlayed``, com o nome do jogo).

Resolve o **nome do jogo** a partir do GPD do dashboard (``FFFE07D1.gpd``) e
**extrai os ícones** (imagem do jogo e, quando presentes no GPD, das conquistas)
para o cache em ``~/ES-DE-STATS/cache/xenia``.

Implementação defensiva (CONQUISTAS.md §3): tolera arquivos truncados, isola
falhas por item e nunca marca desbloqueio incerto como certo.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

from .models import Achievement, GameAchievements, Grade

_XDBF_MAGIC = 0x58444246            # "XDBF"
_NS_ACHIEVEMENT = 1
_NS_IMAGE = 2
_NS_TITLE = 4
_GAME_ICON_ID = 0x8000
_FILETIME_EPOCH = datetime(1601, 1, 1)
_FLAG_UNLOCKED = 0x00020000
_DASHBOARD = "FFFE07D1"
_TITLE_NAME_OFFSET = 0x28


def _u16(b: bytes, o: int) -> int:
    return int.from_bytes(b[o:o + 2], "big")


def _u32(b: bytes, o: int) -> int:
    return int.from_bytes(b[o:o + 4], "big")


def _u64(b: bytes, o: int) -> int:
    return int.from_bytes(b[o:o + 8], "big")


def _utf16be_z(b: bytes, o: int) -> tuple[str, int]:
    end = o
    while end + 1 < len(b) and not (b[end] == 0 and b[end + 1] == 0):
        end += 2
    return b[o:end].decode("utf-16-be", errors="replace"), end + 2


def _cache_root() -> Path:
    env = os.environ.get("ES_DE_STATS_HOME")
    return (Path(env) if env else Path.home() / "ES-DE-STATS") / "cache" / "xenia"


def _entries(data: bytes):
    """Gera (namespace, id, offset_absoluto, length) das entradas do XDBF."""
    if len(data) < 24 or _u32(data, 0) != _XDBF_MAGIC:
        return
    entry_table_len = _u32(data, 8)
    entry_count = _u32(data, 12)
    free_table_len = _u32(data, 16)
    base = 24 + entry_table_len * 18 + free_table_len * 8
    if base > len(data) or entry_count > entry_table_len:
        return
    for i in range(entry_count):
        eo = 24 + i * 18
        if eo + 18 > len(data):
            return
        yield (_u16(data, eo), _u32(data, eo + 2 + 4),  # ns, id (low 32 bits)
               base + _u32(data, eo + 10), _u32(data, eo + 14))


def _title_names(path: Path) -> dict[str, str]:
    """Mapa ``TITLEID_HEX`` -> nome do jogo, a partir do dashboard GPD."""
    out: dict[str, str] = {}
    try:
        data = path.read_bytes()
    except OSError:
        return out
    for ns, _eid, off, length in _entries(data):
        if ns != _NS_TITLE or length < _TITLE_NAME_OFFSET + 2:
            continue
        rec = data[off:off + length]
        tid = _u32(rec, 0)
        name, _ = _utf16be_z(rec, _TITLE_NAME_OFFSET)
        name = name.strip()
        if name:
            out[f"{tid:08X}"] = name
    return out


def _extract_images(data: bytes, cache_dir: Path) -> dict[int, str]:
    """Grava as imagens (ns=2) em cache e devolve ``image_id`` -> caminho."""
    out: dict[int, str] = {}
    for ns, eid, off, length in _entries(data):
        if ns != _NS_IMAGE or length < 8:
            continue
        blob = data[off:off + length]
        if blob[:4] != b"\x89PNG":
            continue
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            target = cache_dir / f"{eid}.png"
            if not target.is_file():
                target.write_bytes(blob)
            out[eid] = str(target)
        except OSError:
            continue
    return out


def _parse_achievement(rec: bytes, images: dict[int, str]) -> Achievement | None:
    if len(rec) < 0x1C:
        return None
    ach_id = _u32(rec, 4)
    image_id = _u32(rec, 8)
    gamerscore = _u32(rec, 0x0C)
    flags = _u32(rec, 0x10)
    ft = _u64(rec, 0x14)
    unlocked = bool(flags & _FLAG_UNLOCKED)
    when: datetime | None = None
    if unlocked and ft:
        try:
            cand = _FILETIME_EPOCH + timedelta(microseconds=ft / 10)
            if 2005 <= cand.year <= 2100:
                when = cand
        except (OverflowError, OSError):
            when = None
    name, nxt = _utf16be_z(rec, 0x1C)
    unlocked_desc, nxt = _utf16be_z(rec, nxt)
    locked_desc, _ = _utf16be_z(rec, nxt)
    return Achievement(
        key=str(ach_id),
        name=name.strip(),
        description=(unlocked_desc or locked_desc).strip(),
        grade=Grade.GAMERSCORE,
        hidden=False,
        unlocked=unlocked,
        unlocked_at=when,
        icon_path=images.get(image_id),
        gamerscore=gamerscore,
    )


def parse_gpd(path: Path, names: dict[str, str] | None = None) -> GameAchievements | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if len(data) < 24 or _u32(data, 0) != _XDBF_MAGIC:
        return None
    title_id = path.stem.upper()
    cache_dir = _cache_root() / title_id
    images = _extract_images(data, cache_dir)

    achievements: list[Achievement] = []
    for ns, _eid, off, length in _entries(data):
        if ns != _NS_ACHIEVEMENT or length < 0x1C:
            continue
        try:
            ach = _parse_achievement(data[off:off + length], images)
        except Exception:
            ach = None
        if ach is not None and ach.name:
            achievements.append(ach)
    if not achievements:
        return None

    title = (names or {}).get(title_id, title_id)
    return GameAchievements(
        emulator="Xenia",
        title=title,
        comm_id=title_id,
        source_path=str(path),
        achievements=achievements,
        progress_available=True,
        icon_path=images.get(_GAME_ICON_ID),
    )


def scan_xenia(root: Path | None) -> list[GameAchievements]:
    if not root or not root.is_dir():
        return []
    gpds = sorted(root.glob("**/*.gpd"))[:800]
    names: dict[str, str] = {}
    for p in gpds:
        if p.stem.upper() == _DASHBOARD:
            names.update(_title_names(p))
    games: list[GameAchievements] = []
    for p in gpds:
        if p.stem.upper() == _DASHBOARD:
            continue
        try:
            g = parse_gpd(p, names)
        except OSError:
            g = None
        if g is not None:
            games.append(g)
    return games
