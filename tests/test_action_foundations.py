from __future__ import annotations

from src.domain import (
    CombatState,
    EntityState,
    Faction,
    GridPos,
    PreparedActionKind,
    ProceduralEncounterGenerator,
    bfs_distances,
    plan_enemy_action,
    validate_encounter,
)


def test_procedural_same_seed_is_reproducible() -> None:
    generator = ProceduralEncounterGenerator()
    first = generator.generate(42042, 1)
    second = generator.generate(42042, 1)
    assert first.fingerprint() == second.fingerprint()
    assert validate_encounter(first)


def test_procedural_different_seeds_are_visibly_different() -> None:
    generator = ProceduralEncounterGenerator()
    first = generator.generate(1)
    second = generator.generate(2)
    assert first.fingerprint() != second.fingerprint()
    changed_tiles = first.floor.symmetric_difference(second.floor)
    assert len(changed_tiles) >= 8


def test_procedural_every_required_cell_is_bfs_reachable() -> None:
    encounter = ProceduralEncounterGenerator().generate(9917, 2)
    distances = bfs_distances(encounter.player_spawn, encounter.floor)
    required = (
        {enemy.pos for enemy in encounter.enemies}
        | set(encounter.hazards)
        | {encounter.reward_pos}
    )
    assert required.issubset(distances)
    assert min(distances[enemy.pos] for enemy in encounter.enemies) >= 7


def _state(kind: str, enemy: GridPos, player: GridPos) -> CombatState:
    return CombatState(
        10,
        8,
        {
            "player": EntityState("player", Faction.PLAYER, player, 8, 8, "ECHO"),
            "enemy": EntityState("enemy", Faction.ENEMY, enemy, 4, 4, kind, kind),
        },
    )


def test_melee_tree_chases_then_attacks() -> None:
    distant = plan_enemy_action(_state("melee", GridPos(1, 1), GridPos(5, 1)), "enemy")
    adjacent = plan_enemy_action(_state("melee", GridPos(4, 1), GridPos(5, 1)), "enemy")
    assert distant.kind is PreparedActionKind.CHASE
    assert adjacent.kind is PreparedActionKind.ATTACK


def test_charger_tree_keeps_distance_then_uses_special() -> None:
    close = plan_enemy_action(
        _state("charger", GridPos(4, 1), GridPos(5, 1)), "enemy", special_ready=True
    )
    aligned = plan_enemy_action(
        _state("charger", GridPos(1, 1), GridPos(5, 1)), "enemy", special_ready=True
    )
    assert close.kind is PreparedActionKind.ATTACK
    assert aligned.kind is PreparedActionKind.SPECIAL


def test_ranged_tree_retreats_strafes_and_shoots() -> None:
    close = plan_enemy_action(_state("ranged", GridPos(3, 1), GridPos(5, 1)), "enemy")
    aligned = plan_enemy_action(_state("ranged", GridPos(1, 1), GridPos(5, 1)), "enemy")
    offset = plan_enemy_action(_state("ranged", GridPos(2, 2), GridPos(5, 1)), "enemy")
    assert close.kind is PreparedActionKind.RETREAT
    assert aligned.kind is PreparedActionKind.ATTACK
    assert offset.kind is PreparedActionKind.STRAFE


def test_prepared_action_is_stable_for_fixed_state() -> None:
    state = _state("charger", GridPos(1, 1), GridPos(5, 1))
    assert plan_enemy_action(state, "enemy", True) == plan_enemy_action(
        state, "enemy", True
    )
