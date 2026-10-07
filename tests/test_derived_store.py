"""Testes do banco derivado: persistência, cursor incremental e presets."""

from datetime import datetime, timezone, timedelta

from esdb.data.derived_store import DerivedStore
from esdb.data.source_adapter import SourceGame
from esdb.domain.models import DurationKind, Session

TZ = timezone(timedelta(hours=-3))


def _store(tmp_path) -> DerivedStore:
    return DerivedStore(tmp_path / "derived.db")


def _session(sid, dur=600):
    s = datetime(2026, 10, 6, 12, 0, tzinfo=TZ)
    return Session(sid, 1, s, s + timedelta(seconds=dur), dur, DurationKind.NORMAL)


def test_incremental_cursor(tmp_path):
    st = _store(tmp_path)
    path = "/x/games.db"
    assert st.get_cursor(path) == 0
    st.upsert_sessions(path, [_session(1), _session(2)])
    st.set_cursor(path, 2)
    assert st.get_cursor(path) == 2
    assert len(st.load_sessions(path)) == 2
    # reimportar as mesmas não duplica (ON CONFLICT DO NOTHING)
    st.upsert_sessions(path, [_session(1), _session(2), _session(3)])
    assert len(st.load_sessions(path)) == 3


def test_games_upsert_updates_mutable_fields(tmp_path):
    st = _store(tmp_path)
    path = "/x/games.db"
    st.upsert_games(path, [SourceGame(1, "Jogo", "PS2", "ps2", "/a.chd")])
    st.upsert_games(path, [SourceGame(1, "Jogo", "PS2", "ps2", "/b.chd")])
    games = st.load_games(path)
    assert len(games) == 1 and games[0].rom == "/b.chd"


def test_presets_roundtrip(tmp_path):
    st = _store(tmp_path)
    st.save_preset("Favoritos", {"platforms": ["PS2"], "options": {"recent7": True}})
    assert "Favoritos" in st.get_presets()
    assert st.get_presets()["Favoritos"]["platforms"] == ["PS2"]
    st.delete_preset("Favoritos")
    assert "Favoritos" not in st.get_presets()


def test_overrides(tmp_path):
    st = _store(tmp_path)
    path = "/x/games.db"
    st.set_override(path, 5, title="Nome Corrigido", cover="/cover.png")
    ov = st.get_overrides(path)
    assert ov[5]["title"] == "Nome Corrigido" and ov[5]["cover"] == "/cover.png"


def test_managed_sources(tmp_path):
    st = _store(tmp_path)
    st.add_managed("Perfil", "/db/perfil.db")
    assert any(m["path"] == "/db/perfil.db" for m in st.list_managed())
    st.remove_managed("/db/perfil.db")
    assert not st.list_managed()
