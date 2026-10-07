"""Teste do parser Xenia (.gpd/XDBF) com um arquivo sintético."""

from datetime import datetime

from esdb.conquistas.models import Grade
from esdb.conquistas.xenia import parse_gpd

_FLAG_UNLOCKED = 0x00020000


def _u16(v): return v.to_bytes(2, "big")
def _u32(v): return v.to_bytes(4, "big")
def _u64(v): return v.to_bytes(8, "big")
def _wz(s): return s.encode("utf-16-be") + b"\x00\x00"


def _filetime(dt: datetime) -> int:
    return int((dt - datetime(1601, 1, 1)).total_seconds() * 10_000_000)


def _achievement_blob(ach_id, gamerscore, flags, ft, name, un, lo) -> bytes:
    body = (_u32(ach_id) + _u32(0) + _u32(gamerscore) + _u32(flags)
            + _u64(ft) + _wz(name) + _wz(un) + _wz(lo))
    size = 4 + len(body)
    return _u32(size) + body


def _make_gpd(achs: list[bytes]) -> bytes:
    entry_count = len(achs)
    entry_table_len = entry_count
    header = (_u32(0x58444246) + _u32(1) + _u32(entry_table_len)
              + _u32(entry_count) + _u32(0) + _u32(0))
    # entry table (18 bytes each): ns(2), id(8), offset(4), length(4)
    entries = b""
    data = b""
    offset = 0
    for i, blob in enumerate(achs):
        entries += _u16(1) + _u64(i + 1) + _u32(offset) + _u32(len(blob))
        data += blob
        offset += len(blob)
    return header + entries + data


def test_parse_gpd_unlocked_and_locked(tmp_path):
    dt = datetime(2026, 3, 15, 10, 0, 0)
    blobs = [
        _achievement_blob(1, 20, _FLAG_UNLOCKED, _filetime(dt),
                          "Primeiro Sangue", "Derrote um inimigo", "???"),
        _achievement_blob(2, 50, 0x0, 0, "Mestre", "Vença o jogo", "???"),
    ]
    gpd = tmp_path / "Jogo.gpd"
    gpd.write_bytes(_make_gpd(blobs))
    g = parse_gpd(gpd)
    assert g is not None and g.emulator == "Xenia"
    assert g.total == 2 and g.unlocked_count == 1
    by = {a.key: a for a in g.achievements}
    assert by["1"].name == "Primeiro Sangue" and by["1"].unlocked
    assert by["1"].grade is Grade.GAMERSCORE and by["1"].gamerscore == 20
    assert by["1"].unlocked_at.year == 2026
    assert not by["2"].unlocked


def test_bad_file_returns_none(tmp_path):
    bad = tmp_path / "x.gpd"
    bad.write_bytes(b"NOTX" + b"\x00" * 40)
    assert parse_gpd(bad) is None
