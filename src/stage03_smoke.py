"""Deterministic formal-entry playtest route used by smoke validation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain import Command, CommandType, Direction, LevelPhase

if TYPE_CHECKING:
    from src.stage03_app import Stage03App


def run_flow_smoke(app: Stage03App) -> None:
    """Traverse menu, all encounters, reward, clear and clean restart."""
    app._start_level()
    app._script_turn(
        Command("player", CommandType.PULL, 1, target_entity_id="charger_alpha"),
        Command("player", CommandType.PUSH, 2, Direction.RIGHT),
        Command("player", CommandType.MOVE, 3, Direction.DOWN),
    )
    if app.scene.value != "reward":
        raise RuntimeError("Stage03 smoke did not reach reward")
    echo_index = next(
        index for index, item in enumerate(app.level_run.reward_choices)
        if item.plugin_id == "echo_protocol"
    )
    app._choose_reward(echo_index)
    app._execute()
    if app.scene.value != "reward":
        raise RuntimeError("Stage04 smoke did not reach second reward")
    app._choose_reward(0)
    if app.level_run.encounter_index != 2:
        raise RuntimeError("Stage03 smoke did not advance to climax")
    scripted = [
        (
            Command("player", CommandType.PULL, 1, target_entity_id="charger_prime"),
            Command("player", CommandType.PUSH, 2, Direction.RIGHT),
            Command("player", CommandType.MOVE, 3, Direction.DOWN),
        ),
        (
            Command("player", CommandType.MOVE, 1, Direction.RIGHT),
            Command("player", CommandType.MOVE, 2, Direction.RIGHT),
            Command("player", CommandType.WAIT, 3),
        ),
        (
            Command("player", CommandType.MOVE, 1, Direction.UP),
            Command("player", CommandType.MOVE, 2, Direction.RIGHT),
            Command("player", CommandType.MOVE, 3, Direction.RIGHT),
        ),
        (
            Command("player", CommandType.PUSH, 1, Direction.RIGHT),
            Command("player", CommandType.PULL, 2, target_entity_id="sniper_prime"),
            Command("player", CommandType.PUSH, 3, Direction.RIGHT),
        ),
    ]
    for commands in scripted:
        app._script_turn(*commands)
    if app.level_run.phase is not LevelPhase.LEVEL_CLEAR:
        raise RuntimeError("Stage03 smoke did not reach Level Clear")
    app._start_level()
    if app.level_run.progress != (1, 3) or app.level_run.player_plugins:
        raise RuntimeError("Stage03 smoke restart did not restore a clean run")
