from __future__ import annotations

import pytest

from src.demo_scenario import create_demo_state, default_commands, winning_commands
from src.domain import (
    Command,
    CommandType,
    CombatState,
    Direction,
    EntityState,
    Faction,
    GridPos,
    execute_turn,
    preview_turn,
    simulate_turn,
    state_fingerprint,
)


def test_clone_changes_do_not_pollute_original() -> None:
    original = create_demo_state()
    cloned = original.clone()
    cloned.entities["player"].hp = 1
    cloned.walls.add(GridPos(0, 0))
    assert original.entities["player"].hp == 3
    assert GridPos(0, 0) not in original.walls


def test_same_input_produces_same_events_and_state() -> None:
    state = create_demo_state()
    first = simulate_turn(state, default_commands())
    second = simulate_turn(state, default_commands())
    assert first.events == second.events
    assert state_fingerprint(first.state) == state_fingerprint(second.state)


def test_empty_slots_are_wait_commands() -> None:
    result = simulate_turn(create_demo_state(), [])
    assert [event.kind for event in result.events[:3]] == ["waited", "waited", "waited"]


def test_preview_matches_real_execution() -> None:
    state = create_demo_state()
    preview = preview_turn(state, winning_commands())
    execution = execute_turn(state, winning_commands())
    assert preview.events == execution.events
    assert preview.state == execution.state
    assert state_fingerprint(preview.state) == state_fingerprint(execution.state)


def test_reordering_same_three_commands_changes_outcome() -> None:
    state = create_demo_state()
    losing = preview_turn(state, default_commands())
    winning = preview_turn(state, winning_commands())
    assert {command.command_type for command in default_commands()} == {
        command.command_type for command in winning_commands()
    }
    assert losing.state.entities["player"].hp == 1
    assert "sniper" in losing.state.entities
    assert winning.state.entities["player"].hp == 3
    assert "sniper" not in winning.state.entities
    assert any(event.kind == "intent_cancelled" for event in winning.events)


def test_move_stops_at_map_edge() -> None:
    state = CombatState(
        2,
        2,
        {"player": EntityState("player", Faction.PLAYER, GridPos(0, 0), 3, 3, "player")},
    )
    command = Command("player", CommandType.MOVE, 1, direction=Direction.LEFT)
    result = simulate_turn(state, [command])
    assert result.state.entities["player"].pos == GridPos(0, 0)
    assert result.events[0].kind == "move_blocked"


def test_push_into_wall_applies_collision_damage() -> None:
    state = CombatState(
        4,
        2,
        {
            "player": EntityState("player", Faction.PLAYER, GridPos(0, 0), 3, 3, "player"),
            "enemy": EntityState("enemy", Faction.ENEMY, GridPos(1, 0), 3, 3, "enemy"),
        },
        walls={GridPos(2, 0)},
    )
    command = Command("player", CommandType.PUSH, 1, direction=Direction.RIGHT)
    result = simulate_turn(state, [command])
    assert result.state.entities["enemy"].pos == GridPos(1, 0)
    assert result.state.entities["enemy"].hp == 1
    assert [event.detail for event in result.events if event.kind == "damaged"] == ["push", "collision"]


def test_dead_actor_loses_later_command() -> None:
    state = CombatState(
        4,
        2,
        {
            "player": EntityState("player", Faction.PLAYER, GridPos(0, 0), 3, 3, "player"),
            "enemy": EntityState("enemy", Faction.ENEMY, GridPos(1, 0), 1, 1, "enemy"),
        },
    )
    commands = [
        Command("player", CommandType.PUSH, 1, direction=Direction.RIGHT),
        Command("enemy", CommandType.MOVE, 2, direction=Direction.DOWN),
    ]
    result = simulate_turn(state, commands)
    assert "enemy" not in result.state.entities
    assert any(event.kind == "command_cancelled" and event.actor_id == "enemy" for event in result.events)


def test_pull_requires_target_in_straight_line_and_range() -> None:
    state = create_demo_state()
    state.entities["sniper"].pos = GridPos(3, 3)
    command = Command("player", CommandType.PULL, 1, target_entity_id="sniper")
    result = simulate_turn(state, [command])
    assert result.state.entities["sniper"].pos == GridPos(3, 3)
    assert result.events[0].kind == "pull_missed"


@pytest.mark.parametrize("slot", [0, 4])
def test_invalid_slot_fails_fast(slot: int) -> None:
    command = Command("player", CommandType.WAIT, slot)
    with pytest.raises(ValueError, match="slot"):
        simulate_turn(create_demo_state(), [command])


def test_duplicate_slot_fails_fast() -> None:
    commands = [
        Command("player", CommandType.WAIT, 1),
        Command("player", CommandType.MOVE, 1, direction=Direction.DOWN),
    ]
    with pytest.raises(ValueError, match="Duplicate"):
        simulate_turn(create_demo_state(), commands)

