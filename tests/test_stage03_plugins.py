from src.domain import (
    Command,
    CommandType,
    CombatState,
    Direction,
    EntityState,
    Faction,
    GridPos,
    simulate_turn,
)


def _state(enemy_pos: GridPos, enemy_hp: int, *effects: str) -> CombatState:
    return CombatState(
        6,
        3,
        {
            "player": EntityState("player", Faction.PLAYER, GridPos(0, 1), 5, 5, "player"),
            "enemy": EntityState("enemy", Faction.ENEMY, enemy_pos, enemy_hp, enemy_hp, "enemy", "guard"),
        },
        player_plugin_effects=effects,
    )


def test_echo_replays_first_command_into_empty_third_slot() -> None:
    state = _state(GridPos(1, 1), 2, "repeat_first_on_empty_third")
    commands = [
        Command("player", CommandType.PUSH, 1, Direction.RIGHT),
        Command("player", CommandType.MOVE, 2, Direction.RIGHT),
    ]
    result = simulate_turn(state, commands)
    assert "enemy" not in result.state.entities
    assert any(event.kind == "plugin_triggered" and event.detail == "echo_protocol" for event in result.events)


def test_kinetic_amplifier_changes_push_damage() -> None:
    normal = simulate_turn(
        _state(GridPos(1, 1), 2), [Command("player", CommandType.PUSH, 1, Direction.RIGHT)]
    )
    amplified = simulate_turn(
        _state(GridPos(1, 1), 2, "push_damage_plus_one"),
        [Command("player", CommandType.PUSH, 1, Direction.RIGHT)],
    )
    assert "enemy" in normal.state.entities
    assert "enemy" not in amplified.state.entities


def test_vector_extender_changes_pull_range() -> None:
    command = Command("player", CommandType.PULL, 1, target_entity_id="enemy")
    normal = simulate_turn(_state(GridPos(3, 1), 2), [command])
    extended = simulate_turn(_state(GridPos(3, 1), 2, "pull_range_plus_one"), [command])
    assert normal.state.entities["enemy"].pos == GridPos(3, 1)
    assert extended.state.entities["enemy"].pos == GridPos(2, 1)


def test_emergency_barrier_changes_shield_amount() -> None:
    result = simulate_turn(
        _state(GridPos(5, 1), 2, "shield_plus_one"),
        [Command("player", CommandType.SHIELD, 1)],
    )
    assert result.state.entities["player"].shield == 2
    assert result.events[0].amount == 2
