"""Normalização de caminhos de ROM.

A fonte grava caminhos com escapes shell (``\\ `` antes de espaços e parênteses),
por exemplo ``/mnt/Games1/ps2/Silent\\ Hill\\ 2\\ \\(USA\\).chd``. A chave de
junção com o ES-DE é o **basename sem extensão** (ESDE.md §4).
"""

from __future__ import annotations

import os
import re

_UNESCAPE = re.compile(r"\\(.)")


def unescape_rom(rom_raw: str) -> str:
    """Remove os escapes de barra invertida do caminho gravado pela fonte."""
    if not rom_raw:
        return ""
    return _UNESCAPE.sub(r"\1", rom_raw)


def rom_basename(rom_raw: str) -> str:
    """Basename do arquivo de ROM, sem diretório e sem extensão.

    ``/mnt/.../Silent\\ Hill\\ 2\\ \\(USA\\).chd`` -> ``Silent Hill 2 (USA)``.
    """
    clean = unescape_rom(rom_raw)
    if not clean:
        return ""
    name = os.path.basename(clean.rstrip("/"))
    stem, _ext = os.path.splitext(name)
    return stem
