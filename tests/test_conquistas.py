"""Testes do parser de conquistas do RPCS3 com arquivos sintéticos."""

from datetime import datetime, timedelta

from esdb.conquistas.models import Grade
from esdb.conquistas.rpcs3 import scan_rpcs3

TROPCONF = """<!--Sce-Np-Trophy-Signature: deadbeef-->
<trophyconf version="1.0">
 <npcommid>NPWR99999_00</npcommid>
 <title-name>Jogo de Teste</title-name>
 <trophy id="000" hidden="no" ttype="P" pid="-1">
  <name>Platina</name><detail>Ganhe tudo.</detail>
 </trophy>
 <trophy id="001" hidden="no" ttype="B" pid="000">
  <name>Primeiro Passo</name><detail>Comece o jogo.</detail>
 </trophy>
 <trophy id="002" hidden="yes" ttype="G" pid="000">
  <name>Segredo</name><detail>Algo oculto.</detail>
 </trophy>
</trophyconf>
"""


def _be(value: int, size: int = 4) -> bytes:
    return value.to_bytes(size, "big")


def _make_tropusr(states: dict[int, tuple[bool, int]]) -> bytes:
    """states: trophy_id -> (unlocked, rtc_microseconds)."""
    count = len(states)
    entry_size = 0x60
    stride = entry_size + 0x10
    offset = 0x30 + 0x20          # 1 tabela
    header = bytearray(offset)
    header[0:4] = _be(0x818F54AD)
    header[8:12] = _be(1)         # tables_count
    # table header em 0x30
    th = bytearray(0x20)
    th[0:4] = _be(6)              # type
    th[4:8] = _be(entry_size)
    th[12:16] = _be(count)
    th[16:24] = _be(offset, 8)
    header[0x30:0x50] = th
    body = bytearray()
    for tid in sorted(states):
        unlocked, rtc = states[tid]
        rec = bytearray(stride)
        rec[0:4] = _be(6)         # record magic
        rec[4:8] = _be(entry_size)
        rec[8:12] = _be(tid)
        pay = 0x10
        rec[pay:pay + 4] = _be(tid)
        rec[pay + 4:pay + 8] = _be(1 if unlocked else 0)
        rec[pay + 0x10:pay + 0x18] = _be(rtc, 8)
        body += rec
    return bytes(header) + bytes(body)


def _rtc(dt: datetime) -> int:
    return int((dt - datetime(1, 1, 1)).total_seconds() * 1_000_000)


def test_definitions_and_progress(tmp_path):
    gdir = tmp_path / "NPWR99999_00"
    gdir.mkdir()
    (gdir / "TROPCONF.SFM").write_text(TROPCONF, encoding="utf-8")
    unlock_dt = datetime(2026, 9, 24, 22, 53, 19)
    (gdir / "TROPUSR.DAT").write_bytes(_make_tropusr({
        0: (False, 0), 1: (True, _rtc(unlock_dt)), 2: (False, 0)}))

    games = scan_rpcs3([tmp_path])
    assert len(games) == 1
    g = games[0]
    assert g.title == "Jogo de Teste"
    assert g.progress_available
    assert g.total == 3 and g.unlocked_count == 1
    by_key = {a.key: a for a in g.achievements}
    assert by_key["000"].grade is Grade.PLATINUM and not by_key["000"].unlocked
    assert by_key["001"].unlocked
    assert by_key["001"].unlocked_at.year == 2026
    # oculto e bloqueado esconde nome/detalhe
    assert by_key["002"].hidden
    assert by_key["002"].display_name() == "Troféu oculto"


def test_progress_unavailable_when_usr_missing(tmp_path):
    gdir = tmp_path / "NPWR88888_00"
    gdir.mkdir()
    (gdir / "TROPCONF.SFM").write_text(TROPCONF, encoding="utf-8")
    games = scan_rpcs3([tmp_path])
    assert len(games) == 1
    assert not games[0].progress_available
    assert games[0].unlocked_count == 0


def test_corrupt_usr_degrades_gracefully(tmp_path):
    gdir = tmp_path / "NPWR77777_00"
    gdir.mkdir()
    (gdir / "TROPCONF.SFM").write_text(TROPCONF, encoding="utf-8")
    (gdir / "TROPUSR.DAT").write_bytes(b"not a real tropusr file")
    games = scan_rpcs3([tmp_path])
    assert len(games) == 1
    assert not games[0].progress_available   # não marca desbloqueio incerto
