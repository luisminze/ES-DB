"""Plataforma exata de jogos do Lutris.

Os scripts do Lutris gravam o **sistema** como ``lutris:<core|runner>`` (o core
libretro, ou o runner). Aqui esse tag vira um nome de plataforma legível, usando
a plataforma do próprio Lutris (``pga.db``) quando o script já a capturou, ou os
mapas abaixo como complemento. Tudo offline e somente leitura.
"""

from __future__ import annotations

# Runner do Lutris → plataforma legível (emuladores dedicados e nativos).
RUNNER_PLATFORM: dict[str, str] = {
    "wine": "Windows", "linux": "Linux", "steam": "Steam",
    "dosbox": "MS-DOS", "scummvm": "ScummVM", "web": "Navegador",
    "flatpak": "Linux", "libretro": "RetroArch",
    "duckstation": "Sony PlayStation", "pcsx2": "Sony PlayStation 2",
    "rpcs3": "Sony PlayStation 3", "ppsspp": "Sony PlayStation Portable",
    "vita3k": "Sony PlayStation Vita", "shadps4": "Sony PlayStation 4",
    "xemu": "Microsoft Xbox", "xenia": "Microsoft Xbox 360",
    "dolphin": "Nintendo GameCube", "cemu": "Nintendo Wii U",
    "yuzu": "Nintendo Switch", "ryujinx": "Nintendo Switch",
    "citra": "Nintendo 3DS", "melonds": "Nintendo DS", "desmume": "Nintendo DS",
    "mupen64plus": "Nintendo 64", "snes9x": "Nintendo SNES (Super Nintendo)",
    "mgba": "Nintendo Game Boy Advance", "mednafen": "Mednafen",
    "flycast": "Sega Dreamcast", "redream": "Sega Dreamcast",
    "mame": "Arcade", "fsuae": "Commodore Amiga", "vice": "Commodore 64",
    "atari800": "Atari 800", "stella": "Atari 2600", "hatari": "Atari ST",
    "o2em": "Magnavox Odyssey²", "openmsx": "MSX", "pico8": "PICO-8",
    "zdoom": "Doom", "easyrpg": "RPG Maker",
}

# Core libretro → plataforma legível (os mais comuns).
CORE_PLATFORM: dict[str, str] = {
    # Nintendo
    "mupen64plus_next": "Nintendo 64", "parallel_n64": "Nintendo 64",
    "nestopia": "Nintendo NES", "fceumm": "Nintendo NES", "mesen": "Nintendo NES",
    "quicknes": "Nintendo NES",
    "snes9x": "Nintendo SNES (Super Nintendo)",
    "snes9x2010": "Nintendo SNES (Super Nintendo)",
    "bsnes": "Nintendo SNES (Super Nintendo)",
    "bsnes_hd_beta": "Nintendo SNES (Super Nintendo)",
    "mesen_s": "Nintendo SNES (Super Nintendo)",
    "gambatte": "Nintendo Game Boy Color", "sameboy": "Nintendo Game Boy",
    "mgba": "Nintendo Game Boy Advance", "vba_next": "Nintendo Game Boy Advance",
    "vbam": "Nintendo Game Boy Advance", "gpsp": "Nintendo Game Boy Advance",
    "desmume": "Nintendo DS", "melonds": "Nintendo DS",
    "citra": "Nintendo 3DS", "dolphin": "Nintendo GameCube",
    "virtualjaguar": "Atari Jaguar",
    # Sony
    "mednafen_psx": "Sony PlayStation", "mednafen_psx_hw": "Sony PlayStation",
    "beetle_psx": "Sony PlayStation", "beetle_psx_hw": "Sony PlayStation",
    "pcsx_rearmed": "Sony PlayStation", "swanstation": "Sony PlayStation",
    "ppsspp": "Sony PlayStation Portable",
    # Sega
    "genesis_plus_gx": "Sega Mega Drive (Genesis)",
    "picodrive": "Sega Mega Drive (Genesis)", "blastem": "Sega Mega Drive (Genesis)",
    "mednafen_saturn": "Sega Saturn", "kronos": "Sega Saturn", "yabause": "Sega Saturn",
    "flycast": "Sega Dreamcast", "smsplus": "Sega Master System",
    # NEC / SNK / Atari / Arcade / outros
    "mednafen_pce": "NEC PC Engine (TurboGrafx-16)",
    "mednafen_pce_fast": "NEC PC Engine (TurboGrafx-16)",
    "beetle_pce": "NEC PC Engine (TurboGrafx-16)",
    "mednafen_ngp": "SNK Neo Geo Pocket", "mednafen_wswan": "Bandai WonderSwan",
    "stella": "Atari 2600", "prosystem": "Atari 7800", "handy": "Atari Lynx",
    "mame": "Arcade", "fbneo": "Arcade", "fbalpha": "Arcade",
    "mame2003_plus": "Arcade", "mame2010": "Arcade",
    "scummvm": "ScummVM", "dosbox_pure": "MS-DOS", "dosbox_core": "MS-DOS",
}


def friendly_platform(system: str | None, fallback: str) -> str:
    """Resolve um ``system`` ``lutris:<tag>`` para o nome de plataforma legível.

    Jogos que não são do Lutris (sem o prefixo) mantêm o ``fallback``.
    """
    if not system or not str(system).startswith("lutris"):
        return fallback
    tag = system.split(":", 1)[1].strip() if ":" in system else ""
    if not tag:
        return fallback or "PC (Lutris)"
    return CORE_PLATFORM.get(tag) or RUNNER_PLATFORM.get(tag) or fallback or "PC (Lutris)"
