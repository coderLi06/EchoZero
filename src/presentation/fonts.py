"""Licensed font selection with deterministic project-local fallbacks."""

from __future__ import annotations

from pathlib import Path

import pygame


ORBITRON_FONT = (
    Path(__file__).resolve().parents[2]
    / "assets"
    / "fonts"
    / "orbitron"
    / "Orbitron-SemiBold.ttf"
)


def load_ui_font(size: int, bold: bool = False, role: str = "body") -> pygame.font.Font:
    """Load Orbitron for Latin display text and system fonts for Chinese/body text."""
    if role == "display_latin" and ORBITRON_FONT.is_file():
        return pygame.font.Font(ORBITRON_FONT, size)
    families = {
        "display": "bahnschriftsemibold,microsoftyahei,simhei,arial",
        "data": "microsoftyahei,simhei,cascadiamono,consolas",
        "body": "microsoftyahei,simhei,segoeui,arial",
    }
    name = pygame.font.match_font(families.get(role, families["body"]))
    font = pygame.font.Font(name, size)
    font.bold = bold
    return font


def text_font_role(text: str, role: str) -> str:
    """Avoid missing CJK glyphs by reserving Orbitron for ASCII display labels."""
    return "display_latin" if role == "display" and text.isascii() else role
