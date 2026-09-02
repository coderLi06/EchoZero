"""Capture deterministic EchoZero UI states for visual QA."""

from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame

from src.action_app import ActionApp
from src.domain import ActionRunPhase, RewardKind
from src.presentation.action_renderer import ActionRenderer


OUTPUT_DIR = Path("artifacts") / "meowa_ui_qa"


def save(renderer: ActionRenderer, app: ActionApp, name: str) -> None:
    renderer.draw(app)
    pygame.image.save(renderer.output, OUTPUT_DIR / f"{name}.png")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pygame.init()
    try:
        output = pygame.Surface((1280, 800))
        renderer = ActionRenderer(output)
        app = ActionApp(seed=10303, meta_path=OUTPUT_DIR / "meta.json")
        app.renderer = renderer
        save(renderer, app, "01_menu_1280x800")

        app.start_new_run()
        save(renderer, app, "02_action_1280x800")
        assert app.run_state is not None
        assert app.run_state.enter_tactical()
        save(renderer, app, "03_tactical_1280x800")
        app.run_state.cancel_tactical()

        for enemy in app.run_state.active_enemies:
            app.run_state.state.entities.pop(enemy.entity_id)
        app.run_state.update(0.01)
        save(renderer, app, "04_reward_1280x800")

        skill_index = next(
            (
                index
                for index, reward in enumerate(app.run_state.reward_choices)
                if reward.kind is RewardKind.SKILL
            ),
            0,
        )
        app._choose_reward(skill_index)
        app.reward_acquired_until = 0
        save(renderer, app, "05_build_1280x800")

        app.run_state.encounter_index = 2
        app.run_state._build_encounter(app.run_state.player.hp)
        save(renderer, app, "06_boss_1280x800")

        app.run_state.encounter_index = 0
        app.run_state._build_encounter(app.run_state.player.hp)
        for width, height in ((1600, 900), (1920, 1080)):
            output = pygame.Surface((width, height))
            renderer.update_viewport_layout(output)
            save(renderer, app, f"07_action_{width}x{height}")

        output = pygame.Surface((1280, 800))
        renderer.update_viewport_layout(output)
        app.run_state.phase = ActionRunPhase.VICTORY
        save(renderer, app, "08_result_1280x800")
        app.run_state.phase = ActionRunPhase.ACTION
        app.debug_panel = True
        save(renderer, app, "09_debug_1280x800")
        app.debug_panel = False
        app.tutorial.start()
        save(renderer, app, "10_tutorial_1280x800")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
