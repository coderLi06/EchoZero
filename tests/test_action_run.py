from __future__ import annotations

from pathlib import Path

from src.domain import (
    ActionRun,
    ActionRunPhase,
    Command,
    CommandType,
    Direction,
    EnemyIntent,
    Faction,
    GridPos,
    PreparedActionKind,
    RewardKind,
    execute_turn,
    preview_turn,
    state_fingerprint,
)
from src.infrastructure import load_demo_content


def _run(seed: int = 100) -> ActionRun:
    _, plugins = load_demo_content(Path(__file__).parents[1] / "data")
    return ActionRun(seed, plugins)


def test_action_run_contains_three_behavior_types() -> None:
    run = _run()
    kinds = {enemy.enemy_kind for enemy in run.active_enemies}
    assert kinds == {"melee", "charger", "ranged"}
    assert {
        action.kind for action in run.prepared_actions.values()
    }.issubset(set(PreparedActionKind))


def test_realtime_move_attack_dodge_and_skill_have_cooldowns() -> None:
    run = _run(8)
    player = run.player
    assert player is not None
    open_direction = next(
        direction
        for direction in Direction
        if player.pos.moved(direction) in run.map.floor
        and run.state.entity_at(player.pos.moved(direction)) is None
    )
    assert run.move_player(open_direction)
    assert run.dodge(open_direction)
    assert run.dodge_cooldown > 0
    assert run.invulnerable > 0
    run.tractor_skill(open_direction)
    assert run.skill_cooldown > 0


def test_encounter_grace_exposes_intent_before_first_enemy_action() -> None:
    run = _run(18)
    origins = {enemy.entity_id: enemy.pos for enemy in run.active_enemies}
    first_enemy = run.active_enemies[0].entity_id

    for _ in range(16):
        run.update(0.1)

    assert round(run.encounter_elapsed, 2) == 1.6
    assert {enemy.entity_id: enemy.pos for enemy in run.active_enemies} == origins
    assert run.enemy_timers[first_enemy] > 0

    run.update(0.1)
    assert run.enemy_timers[first_enemy] >= ActionRun._enemy_interval("melee") - 0.1


def test_enemy_intervals_leave_a_readable_reaction_window() -> None:
    assert ActionRun._enemy_interval("melee") >= 0.95
    assert ActionRun._enemy_interval("charger") > ActionRun._enemy_interval("melee")
    assert ActionRun._enemy_interval("ranged") > ActionRun._enemy_interval("charger")


def test_tactical_intent_is_prepared_behavior_action() -> None:
    run = _run(42)
    before = dict(run.prepared_actions)
    assert run.enter_tactical()
    assert run.phase is ActionRunPhase.TACTICAL
    by_actor = {intent.actor_id: intent for intent in run.state.enemy_intents}
    for actor_id, prepared in before.items():
        intent = by_actor[actor_id]
        assert intent.target_pos == prepared.target_pos
        assert intent.label == prepared.label
        expected_kind = (
            "move"
            if prepared.kind in {
                PreparedActionKind.CHASE,
                PreparedActionKind.RETREAT,
                PreparedActionKind.STRAFE,
                PreparedActionKind.PATROL,
            }
            else "attack"
        )
        assert intent.action_kind == expected_kind


def test_tactical_preview_equals_direct_shared_execution() -> None:
    run = _run(77)
    assert run.enter_tactical()
    player = run.player
    assert player is not None
    direction = next(
        direction
        for direction in Direction
        if player.pos.moved(direction) in run.map.floor
        and run.state.entity_at(player.pos.moved(direction)) is None
    )
    run.set_tactical_command(1, Command("player", CommandType.MOVE, 1, direction))
    preview = run.preview
    direct = execute_turn(run.state, run.commands)
    assert preview is not None
    assert state_fingerprint(preview.state) == state_fingerprint(direct.state)
    result = run.execute_tactical()
    assert result is not None
    assert state_fingerprint(result.state) == state_fingerprint(preview.state)
    assert run.tactical_cooldown == run.TACTICAL_COOLDOWN


def test_tactical_move_intent_uses_shared_simulator() -> None:
    run = _run(17)
    enemy = run.active_enemies[0]
    destination = next(
        pos for pos in run.map.floor
        if pos.manhattan_distance(enemy.pos) == 1
        and run.state.entity_at(pos) is None
    )
    run.state.enemy_intents = (
        EnemyIntent(enemy.entity_id, destination, 0, 1, "move", "CHASE"),
    )
    result = preview_turn(run.state, ())
    assert result.state.entities[enemy.entity_id].pos == destination


def test_reward_mix_changes_build_and_advances_map() -> None:
    run = _run(5)
    for enemy in run.active_enemies:
        del run.state.entities[enemy.entity_id]
    run.update(0.01)
    assert run.phase is ActionRunPhase.REWARD
    assert len(run.reward_choices) == 3
    assert {choice.kind for choice in run.reward_choices} & {
        RewardKind.PROTOCOL,
        RewardKind.SKILL,
        RewardKind.STAT,
    }
    old_map = run.map.fingerprint()
    reward = run.choose_reward(0)
    assert run.encounter_index == 1
    assert run.phase is ActionRunPhase.ACTION
    assert run.map.fingerprint() != old_map
    if reward.kind is RewardKind.PROTOCOL:
        assert reward.protocol_id in run.build


def test_run_reaches_boss_victory_and_defeat() -> None:
    run = _run(9)
    for index in range(run.ENCOUNTER_COUNT):
        for enemy in run.active_enemies:
            del run.state.entities[enemy.entity_id]
        run.update(0.01)
        if index < run.ENCOUNTER_COUNT - 1:
            assert run.phase is ActionRunPhase.REWARD
            run.choose_reward(0)
    assert run.phase is ActionRunPhase.VICTORY

    defeated = _run(10)
    player = defeated.player
    assert player is not None
    player.hp = 0
    del defeated.state.entities["player"]
    defeated.update(0.01)
    assert defeated.phase is ActionRunPhase.DEFEAT


def test_action_state_keeps_domain_free_of_pygame() -> None:
    run = _run()
    assert all(entity.faction in {Faction.PLAYER, Faction.ENEMY} for entity in run.state.entities.values())
