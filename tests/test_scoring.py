"""Testes da pontuação/níveis de conquistas (ES-DB-Update1)."""

from esdb.conquistas.models import Achievement, GameAchievements, Grade
from esdb.conquistas.scoring import (achievement_stats, sony_score,
                                     xbox_gamerscore)


def _ach(grade, unlocked, gs=None):
    return Achievement(key="x", name="n", description="", grade=grade,
                       unlocked=unlocked, gamerscore=gs)


def _game(emulator, achs):
    return GameAchievements(emulator, "Jogo", "ID", "/p", achs)


def test_sony_points_example():
    # 100 bronze + 20 prata + 10 ouro + 2 platina = 3600 pontos
    achs = ([_ach(Grade.BRONZE, True)] * 100 + [_ach(Grade.SILVER, True)] * 20
            + [_ach(Grade.GOLD, True)] * 10 + [_ach(Grade.PLATINUM, True)] * 2)
    score = sony_score([_game("RPCS3", achs)])
    assert score.points == 3600
    assert score.category == "Platina"
    assert score.by_grade[Grade.BRONZE] == 100


def test_sony_levels():
    assert sony_score([_game("RPCS3", [_ach(Grade.BRONZE, True)] * 10)]).category == "Bronze"  # 150
    assert sony_score([_game("RPCS3", [_ach(Grade.SILVER, True)] * 10)]).category == "Prata"  # 300
    s = sony_score([_game("RPCS3", [_ach(Grade.GOLD, True)] * 7)])  # 630
    assert s.category == "Ouro" and s.points == 630


def test_sony_ignores_locked_and_other_emulators():
    achs = [_ach(Grade.GOLD, True), _ach(Grade.GOLD, False)]
    assert sony_score([_game("RPCS3", achs)]).points == 90
    assert sony_score([_game("Xenia", achs)]).points == 0


def test_xbox_gamerscore():
    achs = [_ach(Grade.GAMERSCORE, True, 10), _ach(Grade.GAMERSCORE, True, 20),
            _ach(Grade.GAMERSCORE, True, 50), _ach(Grade.GAMERSCORE, True, 100),
            _ach(Grade.GAMERSCORE, False, 999)]
    assert xbox_gamerscore([_game("Xenia", achs)]) == 180


def test_achievement_stats():
    g1 = _game("RPCS3", [_ach(Grade.BRONZE, True), _ach(Grade.GOLD, True)])  # 2/2 completo
    g2 = _game("Xenia", [_ach(Grade.GAMERSCORE, True, 10), _ach(Grade.GAMERSCORE, False, 20)])
    st = achievement_stats([g1, g2])
    assert st.total_games == 2 and st.completed_games == 1
    assert st.unlocked == 3 and st.total == 4
    assert st.by_platform["RPCS3"] == 2 and st.by_platform["Xenia"] == 1
    assert st.rare_unlocked == 1  # só o ouro
