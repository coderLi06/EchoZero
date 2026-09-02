"""Meowa-authored raster assets used only by the pygame presentation layer."""

from __future__ import annotations

import json
from pathlib import Path

import pygame


ASSET_DIR = Path(__file__).resolve().parents[2] / "assets" / "meowa" / "characters"
ANIMATION_DIR = Path(__file__).resolve().parents[2] / "assets" / "aseprite"


class ActionSpriteLibrary:
    """Load and cache grid-safe unit sprites without affecting game rules."""

    def __init__(self) -> None:
        self._base: dict[str, pygame.Surface] = {}
        self._animations: dict[str, dict[str, tuple[pygame.Surface, ...]]] = {}
        self._oriented: dict[tuple[str, str, int, tuple[int, int], bool], pygame.Surface] = {}
        for name in ("player", "melee", "ranged", "warden"):
            path = ASSET_DIR / f"{name}.png"
            if path.is_file():
                self._base[name] = pygame.image.load(path)
            sheet_path = ANIMATION_DIR / f"{name}.png"
            metadata_path = ANIMATION_DIR / f"{name}.json"
            if sheet_path.is_file() and metadata_path.is_file():
                self._animations[name] = self._load_animation_sheet(sheet_path, metadata_path)

    @staticmethod
    def _load_animation_sheet(
        sheet_path: Path,
        metadata_path: Path,
    ) -> dict[str, tuple[pygame.Surface, ...]]:
        sheet = pygame.image.load(sheet_path)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        frames: list[pygame.Surface] = []
        for item in metadata["frames"].values():
            frame = item["frame"]
            rect = pygame.Rect(frame["x"], frame["y"], frame["w"], frame["h"])
            frames.append(sheet.subsurface(rect).copy())
        animations: dict[str, tuple[pygame.Surface, ...]] = {}
        for tag in metadata["meta"]["frameTags"]:
            animations[tag["name"]] = tuple(frames[tag["from"] : tag["to"] + 1])
        return animations

    def get(
        self,
        kind: str,
        facing: tuple[int, int] = (0, 1),
        *,
        flash: bool = False,
        animation: str = "idle",
        progress: float = 0.0,
    ) -> pygame.Surface | None:
        source_kind = "melee" if kind == "charger" else kind
        clips = self._animations.get(source_kind, {})
        clip = clips.get("hit" if flash and "hit" in clips else animation) or clips.get("idle")
        if clip:
            frame_index = min(len(clip) - 1, max(0, int(progress * len(clip))))
            source = clip[frame_index]
        else:
            frame_index = 0
            source = self._base.get(source_kind)
        if source is None:
            return None
        direction = facing if facing != (0, 0) else (0, 1)
        key = (source_kind, animation, frame_index, direction, flash)
        cached = self._oriented.get(key)
        if cached is not None:
            return cached
        angle = {
            (0, 1): 0,
            (-1, 0): -90,
            (0, -1): 180,
            (1, 0): 90,
        }.get(direction, 0)
        sprite = pygame.transform.rotate(source, angle)
        if flash:
            sprite = sprite.copy()
            sprite.fill((150, 150, 150, 0), special_flags=pygame.BLEND_RGBA_ADD)
        self._oriented[key] = sprite
        return sprite


def draw_meowa_unit(
    surface: pygame.Surface,
    sprite: pygame.Surface,
    center: tuple[int, int],
    *,
    size: int,
    accent: tuple[int, int, int],
    elite: bool = False,
    alpha: int = 255,
) -> None:
    """Draw a crisp sprite with a restrained signal bracket and optional elite mark."""

    scaled = pygame.transform.scale(sprite, (size, size))
    if alpha < 255:
        scaled = scaled.copy()
        scaled.set_alpha(alpha)
    target = scaled.get_rect(center=center)
    shadow = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.ellipse(
        shadow,
        (3, 8, 13, 145),
        pygame.Rect(size // 5, size * 3 // 4, size * 3 // 5, max(4, size // 7)),
    )
    surface.blit(shadow, target)
    surface.blit(scaled, target)

    half = size // 2 - 3
    arm = 6 if elite else 4
    width = 2 if elite else 1
    left, top = center[0] - half, center[1] - half
    right, bottom = center[0] + half, center[1] + half
    pygame.draw.line(surface, accent, (left, top), (left + arm, top), width)
    pygame.draw.line(surface, accent, (left, top), (left, top + arm), width)
    pygame.draw.line(surface, accent, (right, bottom), (right - arm, bottom), width)
    pygame.draw.line(surface, accent, (right, bottom), (right, bottom - arm), width)
    if elite:
        pygame.draw.polygon(
            surface,
            accent,
            ((center[0], top - 4), (center[0] + 4, top), (center[0], top + 4), (center[0] - 4, top)),
            1,
        )
