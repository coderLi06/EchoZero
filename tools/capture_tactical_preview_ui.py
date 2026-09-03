"""Capture deterministic Tactical preview result states for visual QA."""

from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame

from src.action_app import ActionApp
from src.domain import EntityState, Faction, GridPos
from src.presentation.action_renderer import ActionRenderer


OUTPUT_DIR = Path("artifacts") / "tactical_preview_damage"


def save(renderer: ActionRenderer, app: ActionApp, name: str) -> None:
    renderer.draw(app)
    pygame.image.save(renderer.output, OUTPUT_DIR / f"{name}.png")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pygame.init()
    try:
        renderer = ActionRenderer(pygame.Surface((1280, 800)))
        app = ActionApp(seed=10303, meta_path=OUTPUT_DIR / "meta.json")
        app.renderer = renderer
        app.start_new_run()
        run = app.run_state
        assert run is not None
        run.state.width = 5
        run.state.height = 5
        run.state.walls = set()
        run.state.entities = {
            "player": EntityState("player", Faction.PLAYER, GridPos(1, 2), 8, 8, "ECHO"),
            "enemy_3": EntityState(
                "enemy_3", Faction.ENEMY, GridPos(2, 2), 3, 3, "校验射手", "ranged"
            ),
        }
        run.enemy_numbers = {"enemy_3": 3}
        run.prepared_actions = {}
        run.state.enemy_intents = ()
        assert run.enter_tactical()
        save(renderer, app, "01_enemy_hit")

        run.move_tactical_action(0, 3)
        save(renderer, app, "02_no_enemy_hit")
    finally:
        pygame.quit()
        (OUTPUT_DIR / "meta.json").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
