"""Resolução de mídia (capas, screenshots) do ES-DE por junção (ESDE.md §4, §6)."""

from __future__ import annotations

from pathlib import Path

_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


class MediaResolver:
    """Localiza arquivos de mídia por ``system`` + ``basename da ROM``."""

    def __init__(self, resolver) -> None:
        self._resolver = resolver
        self._dir_cache: dict[tuple[str, str], dict[str, Path]] = {}

    def _index(self, system: str, kind: str) -> dict[str, Path]:
        key = (system, kind)
        cached = self._dir_cache.get(key)
        if cached is not None:
            return cached
        index: dict[str, Path] = {}
        folder = self._resolver.media_dir(system, kind)
        if folder.is_dir():
            for entry in folder.iterdir():
                if entry.suffix.lower() in _IMAGE_EXTS and entry.is_file():
                    index.setdefault(entry.stem, entry)
        self._dir_cache[key] = index
        return index

    def cover_for(self, system: str, rom_basename: str) -> Path | None:
        if not system or not rom_basename:
            return None
        return self._index(system, "covers").get(rom_basename)

    def screenshots_for(self, system: str, rom_basename: str) -> list[Path]:
        if not system or not rom_basename:
            return []
        hit = self._index(system, "screenshots").get(rom_basename)
        return [hit] if hit else []
