"""Rótulos de plataforma PC compartilhados pelos launchers (Lutris/Heroic).

Distingue a origem do jogo de PC conforme a loja/SO, para a Biblioteca não
misturar o mesmo título de lojas diferentes (requisito: PC (Windows), PC (Steam),
PC (Epic Games), PC (GOG), PC (Amazon), PC (Linux)).
"""

from __future__ import annotations

PC_WINDOWS = "PC (Windows)"
PC_LINUX = "PC (Linux)"

# Chave de loja (minúscula) → rótulo de plataforma PC.
STORE_PLATFORM: dict[str, str] = {
    "steam": "PC (Steam)",
    "gog": "PC (GOG)",
    "epic": "PC (Epic Games)",
    "egs": "PC (Epic Games)",
    "epicgamesstore": "PC (Epic Games)",
    "legendary": "PC (Epic Games)",
    "amazon": "PC (Amazon)",
    "nile": "PC (Amazon)",
    "humble": PC_WINDOWS,
    "humblebundle": PC_WINDOWS,
    "origin": PC_WINDOWS,
    "ea": PC_WINDOWS,
    "uplay": PC_WINDOWS,
    "ubisoft": PC_WINDOWS,
    "battlenet": PC_WINDOWS,
    "windows": PC_WINDOWS,
    "linux": PC_LINUX,
    "native": PC_LINUX,
}


def pc_platform(store: str | None, os_hint: str | None = None) -> str:
    """Rótulo PC conforme a loja; ``os_hint`` ('linux'/'windows') é o fallback."""
    key = (store or "").strip().lower()
    if key in STORE_PLATFORM:
        return STORE_PLATFORM[key]
    hint = (os_hint or "").strip().lower()
    if hint == "linux":
        return PC_LINUX
    return PC_WINDOWS
