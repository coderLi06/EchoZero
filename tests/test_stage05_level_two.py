from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from src.domain import (
    Command,
    CommandType,
    CombatState,
    Direction,
    EntityState,
    Faction,
    GridPos,
    LevelPhase,
    LevelRun,
    TimelineRule,
    execute_turn,
    prepare_enemy_turn,
    preview_turn,
    state_fingerprint,
)
from src.infrastructure import ContentLoadError, load_demo_content


ECHO_BUILD = ("echo_protocol", "resonance_buffer")
KINETIC_BUILD = ("kinetic_amplifier", "collision_overload")
BARRIER_BUILD = ("emergency_barrier", "aegis_counter")


def _commands(specs: tuple[tuple[str, str | None], ...]) -> tuple[Command, ...]:
    commands: list[Command] = []
    for slot, (kind, argument) in enumerate(specs, start=1):
        command_type = CommandType(kind)
        direction = Direction[argument] if command_type in {CommandType.MOVE, CommandType.PUSH} else None
        target = argument if command_type is CommandType.PULL else None
        commands.append(Command("player", command_type, slot, direction, target))
    return tuple(commands)


COMMON_OPENING = (
    (("move", "DOWN"), ("push", "RIGHT"), ("pull", "reactor_charger")),
    (("move", "RIGHT"), ("move", "UP"), ("push", "RIGHT")),
)

BUILD_ROUTES = {
    ECHO_BUILD: COMMON_OPENING + (
        (("push", "RIGHT"), ("pull", "sweeper_beta"), ("move", "RIGHT")),
        (("pull", "sweeper_beta"), ("push", "RIGHT"), ("wait", None)),
        (("push", "RIGHT"), ("wait", None), ("wait", None)),
        (("move", "LEFT"), ("move", "UP"), ("push", "LEFT")),
    ),
    KINETIC_BUILD: COMMON_OPENING + (
        (("push", "RIGHT"), ("pull", "sweeper_beta"), ("move", "RIGHT")),
        (("wait", None), ("wait", None), ("push", "RIGHT")),
        (("move", "LEFT"), ("move", "UP"), ("push", "LEFT")),
    ),
    BARRIER_BUILD: COMMON_OPENING + (
        (("wait", None), ("move", "DOWN"), ("shield", None)),
        (("push", "RIGHT"), ("pull", "sweeper_beta"), ("move", "RIGHT")),
        (("pull", "sweeper_beta"), ("push", "RIGHT"), ("wait", None)),
        (("wait", None), ("push", "RIGHT"), ("shield", None)),
        (("push", "RIGHT"), ("move", "UP"), ("pull", "charger_delta")),
        (("wait", None), ("wait", None), ("push", "LEFT")),
    ),
}


def _run_level_two(build: tuple[str, ...]) -> LevelRun:
    levels, plugins = load_demo_content()
    run = LevelRun(levels[1], plugins, 1, initial_plugins=build)
    for turn in BUILD_ROUTES[build]:
        for command in _commands(turn):
            run.encounter.set_command(command)
        run.confirm_turn()
    return run


def test_level_two_loads_as_three_encounter_formal_level() -> None:
    levels, plugins = load_demo_content()
    level = levels[1]
    assert level.level_id == "inverse_reactor"
    assert level.theme == "reactor"
    assert len(level.encounters) == 3
    assert level.encounters[-1].is_climax
    assert len(plugins) == 8


def test_reverse_rule_changes_execution_order_and_preview_matches_execute() -> None:
    state = CombatState(
        3,
        3,
        {"player": EntityState("player", Faction.PLAYER, GridPos(0, 0), 3, 3, "P")},
        walls={GridPos(1, 1)},
        timeline_rules=(TimelineRule.REVERSE,),
    )
    commands = (
        Command("player", CommandType.MOVE, 1, Direction.RIGHT),
        Command("player", CommandType.MOVE, 2, Direction.DOWN),
    )
    preview = preview_turn(state, commands)
    executed = execute_turn(state, commands)
    assert preview.state.entities["player"].pos == GridPos(0, 1)
    assert state_fingerprint(preview.state) == state_fingerprint(executed.state)
    assert any(event.kind == "rule_triggered" for event in preview.events)


def test_rule_node_holds_phase_while_leaving_node_advances_it() -> None:
    base = CombatState(
        3,
        3,
        {"player": EntityState("player", Faction.PLAYER, GridPos(1, 1), 3, 3, "P")},
        timeline_rules=(TimelineRule.REVERSE, TimelineRule.STABLE),
        rule_nodes=frozenset({GridPos(1, 1)}),
    )
    held = execute_turn(base, ())
    assert held.state.active_timeline_rule is TimelineRule.REVERSE
    assert any(event.kind == "rule_held" for event in held.events)
    moved = execute_turn(
        base, [Command("player", CommandType.MOVE, 3, Direction.RIGHT)]
    )
    assert moved.state.active_timeline_rule is TimelineRule.STABLE
    assert any(event.kind == "rule_changed" for event in moved.events)


def test_sweeper_and_warden_publish_multiple_deterministic_intents() -> None:
    sweeper_state = CombatState(
        8,
        6,
        {
            "player": EntityState("player", Faction.PLAYER, GridPos(1, 2), 6, 6, "P"),
            "sweeper": EntityState("sweeper", Faction.ENEMY, GridPos(5, 2), 2, 2, "S", "sweeper"),
        },
    )
    prepared, _ = prepare_enemy_turn(sweeper_state)
    assert [intent.target_pos for intent in prepared.enemy_intents] == [GridPos(1, 2), GridPos(1, 3)]

    warden_state = sweeper_state.clone()
    warden_state.entities["sweeper"].enemy_kind = "warden"
    prepared, _ = prepare_enemy_turn(warden_state)
    assert len(prepared.enemy_intents) == 3


def test_level_two_inherits_hp_and_build_and_restart_restores_inherited_state() -> None:
    levels, plugins = load_demo_content()
    run = LevelRun(
        levels[1], plugins, 88, initial_player_hp=4, initial_plugins=ECHO_BUILD
    )
    assert run.encounter.state.entities["player"].hp == 4
    assert run.encounter.state.player_plugins == ECHO_BUILD
    run.player_hp = 1
    run.player_plugins.append("tractor_lock")
    run.restart(88)
    assert run.player_hp == 4
    assert run.player_plugins == list(ECHO_BUILD)


@pytest.mark.parametrize("build", [ECHO_BUILD, KINETIC_BUILD, BARRIER_BUILD])
def test_each_stage04_build_completes_level_two(build: tuple[str, ...]) -> None:
    run = _run_level_two(build)
    assert run.phase is LevelPhase.LEVEL_CLEAR
    assert run.player_hp == 6
    assert run.completed_encounters == {
        "inverse_ignition", "sweep_interference", "zero_phase_finale"
    }


def test_three_build_routes_require_different_turn_counts_and_commands() -> None:
    lengths = {build: len(route) for build, route in BUILD_ROUTES.items()}
    assert lengths[ECHO_BUILD] == 6
    assert lengths[KINETIC_BUILD] == 5
    assert lengths[BARRIER_BUILD] == 8
    assert BUILD_ROUTES[ECHO_BUILD] != BUILD_ROUTES[KINETIC_BUILD]
    assert BUILD_ROUTES[BARRIER_BUILD] != BUILD_ROUTES[ECHO_BUILD]


def test_level_two_defeat_and_final_encounter_are_reachable() -> None:
    levels, plugins = load_demo_content()
    run = LevelRun(levels[1], plugins, 1, initial_player_hp=1, initial_plugins=ECHO_BUILD)
    while run.phase is LevelPhase.BATTLE:
        run.confirm_turn()
    assert run.phase is LevelPhase.DEFEAT

    winner = _run_level_two(KINETIC_BUILD)
    assert "zero_phase_finale" in winner.completed_encounters


def test_bad_timeline_rule_fails_fast(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[1] / "data"
    root = tmp_path / "data"
    shutil.copytree(source, root)
    level_path = root / "levels" / "level_2.json"
    payload = json.loads(level_path.read_text(encoding="utf-8"))
    payload["encounters"][0]["rule_cycle"] = ["unknown_phase"]
    level_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ContentLoadError, match="unknown value"):
        load_demo_content(root)
