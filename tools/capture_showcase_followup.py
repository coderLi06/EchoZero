"""Capture Level 1 climax after the first enemy falls and commands are renewed."""

from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame

from src.domain import Command, CommandType, Direction
from src.presentation.stage03_renderer import Stage03Renderer
from src.stage03_app import AppScene, Stage03App


OUTPUT_DIR = Path("artifacts") / "showcase_followup"


def set_commands(app: Stage03App, commands: tuple[Command, ...]) -> None:
    for command in commands:
        app.level_run.encounter.set_command(command)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pygame.init()
    try:
        app = Stage03App(seed=10303, metrics_path=OUTPUT_DIR / "metrics.txt")
        app._start_level()
        app._skip_all_tutorial()
        set_commands(app, (
            Command("player", CommandType.PULL, 1, target_entity_id="charger_alpha"),
            Command("player", CommandType.PUSH, 2, Direction.RIGHT),
            Command("player", CommandType.MOVE, 3, Direction.DOWN),
        ))
        app._execute()
        echo_index = next(
            index for index, reward in enumerate(app.level_run.reward_choices)
            if reward.plugin_id == "echo_protocol"
        )
        app._choose_reward(echo_index)
        set_commands(app, (
            Command("player", CommandType.PUSH, 1, Direction.RIGHT),
            Command("player", CommandType.MOVE, 2, Direction.RIGHT),
            Command("player", CommandType.WAIT, 3),
        ))
        app._execute()
        app._choose_reward(0)
        set_commands(app, (
            Command("player", CommandType.PULL, 1, target_entity_id="charger_prime"),
            Command("player", CommandType.PUSH, 2, Direction.RIGHT),
            Command("player", CommandType.MOVE, 3, Direction.DOWN),
        ))
        app._execute()
        assert app.scene is AppScene.BATTLE
        assert all(
            command.command_type is not CommandType.WAIT
            for command in app.level_run.encounter.commands
        )
        output = pygame.Surface((1280, 800))
        renderer = Stage03Renderer(output)
        app.renderer = renderer
        renderer.draw(app)
        pygame.image.save(output, OUTPUT_DIR / "01_second_plan_ready.png")
    finally:
        pygame.quit()
        (OUTPUT_DIR / "metrics.txt").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
