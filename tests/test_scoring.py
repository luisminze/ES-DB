"""Testes dos agregados (distribuição) de conquistas — sem pontuação."""

from esdb.conquistas.models import Achievement, GameAchievements, Grade
from esdb.conquistas.scoring import achievement_stats


def _ach(grade, unlocked, gs=None):
    return Achievement(key="x", name="n", description="", grade=grade,
                       unlocked=unlocked, gamerscore=gs)


def _game(emulator, achs):
    return GameAchievements(emulator, "Jogo", "ID", "/p", achs)


def test_achievement_stats():
    g1 = _game("RPCS3", [_ach(Grade.BRONZE, True), _ach(Grade.GOLD, True)])  # 2/2 completo
    g2 = _game("Xenia", [_ach(Grade.GAMERSCORE, True, 10), _ach(Grade.GAMERSCORE, False, 20)])
    st = achievement_stats([g1, g2])
    assert st.total_games == 2 and st.completed_games == 1
    assert st.unlocked == 3 and st.total == 4
    assert st.by_platform["RPCS3"] == 2 and st.by_platform["Xenia"] == 1
    assert st.rare_unlocked == 1  # só o ouro


def test_no_scoring_api():
    """A pontuação (Sony points / gamerscore / níveis) foi removida."""
    import esdb.conquistas.scoring as s
    assert not hasattr(s, "sony_score")
    assert not hasattr(s, "xbox_gamerscore")
    assert not hasattr(s, "SonyScore")
