from __future__ import annotations

import json
from pathlib import Path

import pygame

from src.domain import Command, CommandType, Direction
from src.presentation.action_assets import ActionSpriteLibrary
from src.presentation.action_renderer import ActionRenderer, COLORS


ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "aseprite"


def test_aseprite_sheets_have_stable_64px_frames_and_required_tags() -> None:
    expected = {
        "player": {"idle", "move", "attack", "dodge", "hurt"},
        "melee": {"idle", "prepared", "attack", "hit", "death"},
        "ranged": {"idle", "prepared", "attack", "hit", "death"},
        "warden": {"idle", "prepared", "attack", "hit", "death"},
    }
    for name, tags in expected.items():
        metadata = json.loads((ASSET_DIR / f"{name}.json").read_text(encoding="utf-8"))
        assert metadata["meta"]["size"]["h"] == 64
        assert metadata["meta"]["size"]["w"] % 64 == 0
        assert {tag["name"] for tag in metadata["meta"]["frameTags"]} == tags
        assert metadata["meta"]["slices"][0]["name"] == "foot_anchor"


def test_sprite_library_uses_distinct_animation_frames() -> None:
    pygame.init()
    library = ActionSpriteLibrary()
    early = library.get("player", Direction.RIGHT.delta, animation="move", progress=0.05)
    late = library.get("player", Direction.RIGHT.delta, animation="move", progress=0.8)
    assert early is not None and late is not None
    assert early.get_size() == late.get_size() == (64, 64)
    assert pygame.image.tobytes(early, "RGBA") != pygame.image.tobytes(late, "RGBA")


def test_tactical_chain_labels_are_player_facing_and_visual_only() -> None:
    pull_push_move = [
        Command("player", CommandType.PULL, 1, Direction.RIGHT),
        Command("player", CommandType.PUSH, 2, Direction.RIGHT),
        Command("player", CommandType.MOVE, 3, Direction.LEFT),
    ]
    shield_push_wait = [
        Command("player", CommandType.SHIELD, 1),
        Command("player", CommandType.PUSH, 2, Direction.RIGHT),
        Command("player", CommandType.WAIT, 3),
    ]
    assert ActionRenderer._tactical_chain(pull_push_move) == (
        "锁断 · 拉近 → 击退 → 脱离",
        COLORS["violet"],
    )
    assert ActionRenderer._tactical_chain(shield_push_wait) == (
        "盾势 · 先防御后反推",
        COLORS["success"],
    )
