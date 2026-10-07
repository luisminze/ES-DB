from esdb.esde.rom import rom_basename, unescape_rom
from esdb.esde.gamelist import _basename_of, _parse_rating


def test_unescape_rom():
    raw = r"/mnt/Games1/ps2/Silent\ Hill\ 2\ \(USA\)\ \(PlayStation\ 2\).chd"
    assert unescape_rom(raw) == "/mnt/Games1/ps2/Silent Hill 2 (USA) (PlayStation 2).chd"


def test_rom_basename_matches_media_name():
    raw = r"/mnt/Games1/ps2/Silent\ Hill\ 2\ \(USA\)\ \(PlayStation\ 2\).chd"
    assert rom_basename(raw) == "Silent Hill 2 (USA) (PlayStation 2)"


def test_rom_basename_handles_zar_and_cso():
    assert rom_basename(r"/x/Forza\ Horizon\ 2\ \(USA\).zar") == "Forza Horizon 2 (USA)"
    assert rom_basename("") == ""


def test_gamelist_basename_strips_dot_slash():
    assert _basename_of("./Black (USA) (PlayStation 2).chd") == "Black (USA) (PlayStation 2)"


def test_rating_clamped():
    assert _parse_rating("0.8") == 0.8
    assert _parse_rating("bad") is None
    assert _parse_rating("2") == 1.0
