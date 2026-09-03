from __future__ import annotations

import pytest

from src.domain import (
    Command,
    CommandType,
    CombatState,
    Direction,
    Encounter,
    EncounterOutcome,
    EnemyIntent,
    EntityState,
    Faction,
    GridPos,
    prepare_enemy_turn,
    simulate_turn,
    state_fingerprint,
)
from src.stage02_scenario import create_stage02_state, opening_commands


def _set_commands(encounter: Encounter, commands: list[Command]) -> None:
    for command in commands:
        encounter.set_command(command)


def test_encounter_initialises_two_enemy_types_and_public_intent() -> None:
    encounter = Encounter(create_stage02_state())
    assert encounter.outcome is EncounterOutcome.ONGOING
    assert {entity.enemy_kind for entity in encounter.state.entities.values() if entity.faction is Faction.ENEMY} == {"charger", "sniper"}
    assert encounter.state.entities["charger"].pos == GridPos(3, 3)
    assert encounter.state.enemy_intents == (EnemyIntent("charger", GridPos(1, 3), 1, 1),)


def test_fixed_state_produces_fixed_bfs_plan() -> None:
    state = create_stage02_state()
    first_state, first_events = prepare_enemy_turn(state)
    second_state, second_events = prepare_enemy_turn(state)
    assert state_fingerprint(first_state) == state_fingerprint(second_state)
    assert first_events == second_events


def test_illegal_command_does_not_change_encounter() -> None:
    encounter = Encounter(create_stage02_state())
    before = state_fingerprint(encounter.state)
    before_commands = list(encounter.commands)
    with pytest.raises(ValueError, match="direction"):
        encounter.set_command(Command("player", CommandType.MOVE, 1))
    assert state_fingerprint(encounter.state) == before
    assert encounter.commands == before_commands


def test_dead_target_fallback_waits_only_when_player_has_no_legal_action() -> None:
    state = CombatState(
        3,
        3,
        {
            "player": EntityState("player", Faction.PLAYER, GridPos(1, 1), 5, 5, "Player"),
            "enemy": EntityState("enemy", Faction.ENEMY, GridPos(0, 0), 2, 2, "Enemy", "guard"),
        },
        walls={GridPos(1, 0), GridPos(2, 1), GridPos(1, 2), GridPos(0, 1)},
    )

    replacement = Encounter._approach_surviving_enemy(state, 2)

    assert replacement == Command("player", CommandType.WAIT, 2)


def test_shield_changes_state_and_absorbs_enemy_damage() -> None:
    state = CombatState(
        3,
        2,
        {
            "player": EntityState("player", Faction.PLAYER, GridPos(0, 0), 3, 3, "player"),
            "enemy": EntityState("enemy", Faction.ENEMY, GridPos(2, 0), 2, 2, "enemy", "sniper"),
        },
        enemy_intents=(EnemyIntent("enemy", GridPos(0, 0), 2, 1),),
    )
    result = simulate_turn(state, [Command("player", CommandType.SHIELD, 1)])
    assert result.state.entities["player"].hp == 2
    assert result.state.entities["player"].shield == 0
    assert any(event.kind == "shield_absorbed" for event in result.events)


def test_reordering_opening_commands_changes_first_turn_result() -> None:
    losing = Encounter(create_stage02_state())
    _set_commands(losing, opening_commands())
    losing_result = losing.preview()

    winning = Encounter(create_stage02_state())
    defaults = opening_commands()
    _set_commands(winning, [defaults[2].in_slot(1), defaults[0].in_slot(2), defaults[1].in_slot(3)])
    winning_result = winning.preview()

    assert losing_result.state.entities["player"].hp == 5
    assert "charger" in losing_result.state.entities
    assert winning_result.state.entities["player"].hp == 5
    assert "charger" not in winning_result.state.entities
    assert any(event.kind == "intent_cancelled" for event in winning_result.events)


def test_enemy_intent_executes_and_can_kill_player() -> None:
    encounter = Encounter(create_stage02_state())
    for _ in range(3):
        resolution = encounter.confirm_turn()
    assert resolution.outcome is EncounterOutcome.DEFEAT
    assert "player" not in encounter.state.entities


def test_full_stage02_encounter_can_reach_victory() -> None:
    encounter = Encounter(create_stage02_state())
    defaults = opening_commands()
    _set_commands(encounter, [defaults[2].in_slot(1), defaults[0].in_slot(2), defaults[1].in_slot(3)])
    first = encounter.confirm_turn()
    assert "charger" not in encounter.state.entities
    assert first.outcome is EncounterOutcome.ONGOING

    _set_commands(encounter, [
        Command("player", CommandType.MOVE, 1, direction=Direction.RIGHT),
        Command("player", CommandType.MOVE, 2, direction=Direction.RIGHT),
        Command("player", CommandType.WAIT, 3),
    ])
    encounter.confirm_turn()
    _set_commands(encounter, [
        Command("player", CommandType.MOVE, 1, direction=Direction.UP),
        Command("player", CommandType.MOVE, 2, direction=Direction.RIGHT),
        Command("player", CommandType.MOVE, 3, direction=Direction.RIGHT),
    ])
    encounter.confirm_turn()
    _set_commands(encounter, [
        Command("player", CommandType.PUSH, 1, direction=Direction.RIGHT),
        Command("player", CommandType.PULL, 2, target_entity_id="sniper"),
        Command("player", CommandType.PUSH, 3, direction=Direction.RIGHT),
    ])
    result = encounter.confirm_turn()
    assert result.outcome is EncounterOutcome.VICTORY
    assert all(entity.faction is not Faction.ENEMY for entity in encounter.state.entities.values())


def test_restart_after_defeat_restores_clean_initial_state() -> None:
    encounter = Encounter(create_stage02_state())
    for _ in range(3):
        encounter.confirm_turn()
    assert encounter.outcome is EncounterOutcome.DEFEAT
    encounter.restart()
    clean = Encounter(create_stage02_state())
    assert encounter.outcome is EncounterOutcome.ONGOING
    assert state_fingerprint(encounter.state) == state_fingerprint(clean.state)
    assert encounter.commands == clean.commands
