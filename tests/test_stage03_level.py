from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.domain import Command, CommandType, Direction, LevelPhase
from src.domain.level import LevelRun
from src.infrastructure import ContentLoadError, load_level_one


def _set(run: LevelRun, commands: list[Command]) -> None:
    for command in commands:
        run.encounter.set_command(command)


def _win_first_encounter(run: LevelRun) -> None:
    _set(
        run,
        [
            Command("player", CommandType.PULL, 1, target_entity_id="charger_alpha"),
            Command("player", CommandType.PUSH, 2, Direction.RIGHT),
            Command("player", CommandType.MOVE, 3, Direction.DOWN),
        ],
    )
    run.confirm_turn()


def test_level_one_initialises_in_configured_order() -> None:
    level, plugins = load_level_one()
    run = LevelRun(level, plugins)
    assert level.level_id == "calibration_chamber"
    assert [item.encounter_id for item in level.encounters] == [
        "sequence_calibration",
        "protocol_trial",
        "dual_lock_climax",
    ]
    assert run.phase is LevelPhase.BATTLE
    assert run.progress == (1, 3)
    assert run.encounter.state.entities["charger_alpha"].enemy_kind == "charger"


def test_reward_applies_and_player_state_inherits_but_enemy_state_does_not() -> None:
    level, plugins = load_level_one()
    run = LevelRun(level, plugins)
    _win_first_encounter(run)
    assert run.phase is LevelPhase.REWARD
    assert {item.plugin_id for item in run.reward_choices} == {
        "echo_protocol",
        "kinetic_amplifier",
        "emergency_barrier",
    }

    run.choose_reward("echo_protocol")
    assert run.phase is LevelPhase.BATTLE
    assert run.progress == (2, 3)
    assert run.encounter.state.player_plugins == ("echo_protocol",)
    assert run.encounter.state.entities["player"].hp == 6
    assert "charger_alpha" not in run.encounter.state.entities
    assert set(run.encounter.state.entities) == {"player", "guard_beta"}


def test_echo_choice_changes_second_encounter_and_advances_to_climax() -> None:
    level, plugins = load_level_one()
    run = LevelRun(level, plugins)
    _win_first_encounter(run)
    run.choose_reward("echo_protocol")
    _set(
        run,
        [
            Command("player", CommandType.PUSH, 1, Direction.RIGHT),
            Command("player", CommandType.MOVE, 2, Direction.RIGHT),
            Command("player", CommandType.WAIT, 3),
        ],
    )
    preview = run.encounter.preview()
    assert "guard_beta" not in preview.state.entities
    run.confirm_turn()
    assert run.phase is LevelPhase.REWARD
    run.choose_reward(run.reward_choices[0].plugin_id)
    assert run.progress == (3, 3)
    assert run.phase is LevelPhase.BATTLE
    assert set(run.encounter.state.entities) == {"player", "charger_prime", "sniper_prime"}


def test_climax_second_turn_keeps_actions_after_first_enemy_is_defeated() -> None:
    level, plugins = load_level_one()
    run = LevelRun(level, plugins)
    _win_first_encounter(run)
    run.choose_reward("echo_protocol")
    _set(
        run,
        [
            Command("player", CommandType.PUSH, 1, Direction.RIGHT),
            Command("player", CommandType.MOVE, 2, Direction.RIGHT),
            Command("player", CommandType.WAIT, 3),
        ],
    )
    run.confirm_turn()
    run.choose_reward(run.reward_choices[0].plugin_id)
    _set(
        run,
        [
            Command("player", CommandType.PULL, 1, target_entity_id="charger_prime"),
            Command("player", CommandType.PUSH, 2, Direction.RIGHT),
            Command("player", CommandType.MOVE, 3, Direction.DOWN),
        ],
    )

    resolution = run.confirm_turn()

    assert resolution.outcome.value == "ongoing"
    assert set(run.encounter.state.entities) == {"player", "sniper_prime"}
    assert all(
        command.target_entity_id != "charger_prime"
        for command in run.encounter.commands
    )
    assert all(
        command.command_type is not CommandType.WAIT
        for command in run.encounter.commands
    )
    assert run.encounter.preview().state.turn == run.encounter.state.turn + 1


def test_restart_clears_progress_build_and_restores_health() -> None:
    level, plugins = load_level_one()
    run = LevelRun(level, plugins)
    _win_first_encounter(run)
    run.choose_reward("echo_protocol")
    run.restart()
    assert run.progress == (1, 3)
    assert run.phase is LevelPhase.BATTLE
    assert run.player_plugins == []
    assert run.encounter.state.entities["player"].hp == level.player_max_hp


def test_level_defeat_triggers_when_player_core_is_destroyed() -> None:
    level, plugins = load_level_one()
    run = LevelRun(level, plugins)
    while run.phase is LevelPhase.BATTLE:
        run.confirm_turn()
    assert run.phase is LevelPhase.DEFEAT
    assert "player" not in run.encounter.state.entities


def test_illegal_duplicate_settlement_is_rejected() -> None:
    level, plugins = load_level_one()
    run = LevelRun(level, plugins)
    _win_first_encounter(run)
    with pytest.raises(RuntimeError, match="reward"):
        run.confirm_turn()


def test_missing_resource_has_readable_error(tmp_path: Path) -> None:
    with pytest.raises(ContentLoadError, match="Missing content file"):
        load_level_one(tmp_path)


def test_duplicate_plugin_id_and_bad_reference_fail_fast(tmp_path: Path) -> None:
    plugins_dir = tmp_path / "plugins"
    levels_dir = tmp_path / "levels"
    plugins_dir.mkdir()
    levels_dir.mkdir()
    duplicate = {
        "plugins": [
            {"id": "same", "name": "A", "description": "A", "effect_type": "shield_plus_one"},
            {"id": "same", "name": "B", "description": "B", "effect_type": "shield_plus_one"},
        ]
    }
    (plugins_dir / "protocols.json").write_text(json.dumps(duplicate), encoding="utf-8")
    with pytest.raises(ContentLoadError, match="duplicate plugin id"):
        load_level_one(tmp_path)

    valid_plugins = {
        "plugins": [
            {"id": "known", "name": "A", "description": "A", "effect_type": "shield_plus_one"}
        ]
    }
    bad_level = {
        "id": "bad",
        "name": "Bad",
        "seed": 1,
        "width": 2,
        "height": 2,
        "player_max_hp": 2,
        "encounters": [
            {
                "id": "one",
                "title": "One",
                "objective": "Win",
                "hint": "Hint",
                "player_spawn": [0, 0],
                "enemies": [{"id": "enemy", "name": "E", "kind": "guard", "pos": [1, 0], "hp": 1}],
                "reward_choices": ["missing"]
            }
        ]
    }
    (plugins_dir / "protocols.json").write_text(json.dumps(valid_plugins), encoding="utf-8")
    (levels_dir / "level_1.json").write_text(json.dumps(bad_level), encoding="utf-8")
    with pytest.raises(ContentLoadError, match="unknown plugin"):
        load_level_one(tmp_path)
