"""Build deterministic Aseprite-ready animation sheets from approved Meowa sprites."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "assets" / "meowa" / "characters"
OUTPUT_DIR = ROOT / "assets" / "aseprite"
FRAME_SIZE = 64

PLAYER_TAGS = (
    ("idle", 2, 280),
    ("move", 4, 75),
    ("attack", 3, 55),
    ("dodge", 2, 70),
    ("hurt", 1, 120),
)
ENEMY_TAGS = (
    ("idle", 2, 280),
    ("prepared", 2, 120),
    ("attack", 3, 65),
    ("hit", 1, 100),
    ("death", 4, 70),
)


def _shift(source: pygame.Surface, dx: int = 0, dy: int = 0) -> pygame.Surface:
    frame = pygame.Surface((FRAME_SIZE, FRAME_SIZE), pygame.SRCALPHA)
    frame.blit(source, (dx, dy))
    return frame


def _flash(source: pygame.Surface, color: tuple[int, int, int]) -> pygame.Surface:
    frame = source.copy()
    overlay = pygame.Surface(frame.get_size(), pygame.SRCALPHA)
    overlay.fill((*color, 0))
    frame.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    return frame


def _player_frames(source: pygame.Surface) -> list[pygame.Surface]:
    frames = [
        _shift(source),
        _shift(source, 0, -1),
        _shift(source, -1, 0),
        _shift(source, 0, -1),
        _shift(source, 1, 0),
        _shift(source, 0, 1),
        _shift(source, -2, 0),
        _shift(source, 3, -1),
        _shift(source, 1, 0),
        _shift(source, -2, 0),
        _shift(source, 3, 0),
        _flash(source, (150, 150, 150)),
    ]
    pygame.draw.line(frames[7], (249, 252, 255, 230), (42, 24), (59, 12), 2)
    pygame.draw.line(frames[7], (78, 226, 255, 210), (44, 28), (61, 18), 1)
    frames[9].set_alpha(170)
    return frames


def _enemy_frames(source: pygame.Surface, accent: tuple[int, int, int]) -> list[pygame.Surface]:
    frames = [_shift(source), _shift(source, 0, -1)]
    for inset in (5, 2):
        frame = _shift(source)
        pygame.draw.rect(frame, (*accent, 210), pygame.Rect(inset, inset, 64 - inset * 2, 64 - inset * 2), 1)
        frames.append(frame)
    frames.extend((_shift(source, -1, 0), _shift(source, 3, 0), _shift(source, 1, 0)))
    frames.append(_flash(source, (170, 170, 170)))
    for step in range(4):
        frame = pygame.Surface((FRAME_SIZE, FRAME_SIZE), pygame.SRCALPHA)
        cutoff = step * 16
        if cutoff < FRAME_SIZE:
            frame.blit(source, (0, cutoff), pygame.Rect(0, cutoff, FRAME_SIZE, FRAME_SIZE - cutoff))
            pygame.draw.line(frame, (*accent, 220), (4, cutoff), (59, cutoff), 1)
        frame.set_alpha(255 - step * 55)
        frames.append(frame)
    return frames


def _write_sheet(name: str, frames: list[pygame.Surface], tags: tuple[tuple[str, int, int], ...]) -> None:
    sheet = pygame.Surface((len(frames) * FRAME_SIZE, FRAME_SIZE), pygame.SRCALPHA)
    metadata_frames: dict[str, dict[str, object]] = {}
    for index, frame in enumerate(frames):
        sheet.blit(frame, (index * FRAME_SIZE, 0))
        metadata_frames[f"{name}_{index:02d}"] = {
            "frame": {"x": index * FRAME_SIZE, "y": 0, "w": FRAME_SIZE, "h": FRAME_SIZE},
            "duration": 100,
        }
    frame_tags: list[dict[str, object]] = []
    cursor = 0
    for tag_name, count, duration in tags:
        for index in range(cursor, cursor + count):
            metadata_frames[f"{name}_{index:02d}"]["duration"] = duration
        frame_tags.append({"name": tag_name, "from": cursor, "to": cursor + count - 1, "direction": "forward"})
        cursor += count
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pygame.image.save(sheet, OUTPUT_DIR / f"{name}.png")
    metadata = {
        "frames": metadata_frames,
        "meta": {
            "app": "EchoZero Aseprite-compatible pipeline",
            "image": f"{name}.png",
            "format": "RGBA8888",
            "size": {"w": sheet.get_width(), "h": FRAME_SIZE},
            "scale": "1",
            "frameTags": frame_tags,
            "slices": [{"name": "foot_anchor", "keys": [{"frame": 0, "bounds": {"x": 31, "y": 51, "w": 2, "h": 2}}]}],
        },
    }
    (OUTPUT_DIR / f"{name}.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    pygame.init()
    accents = {"melee": (255, 104, 112), "ranged": (198, 153, 255), "warden": (92, 235, 173)}
    for name in ("player", "melee", "ranged", "warden"):
        source_path = SOURCE_DIR / f"{name}.png"
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        source = pygame.image.load(source_path)
        source = pygame.transform.scale(source, (FRAME_SIZE, FRAME_SIZE))
        if name == "player":
            _write_sheet(name, _player_frames(source), PLAYER_TAGS)
        else:
            _write_sheet(name, _enemy_frames(source, accents[name]), ENEMY_TAGS)
    print(f"Built Aseprite-ready sheets in {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
