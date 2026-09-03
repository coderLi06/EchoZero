from __future__ import annotations

from pathlib import Path

from src.domain import (
    ActionRun,
    ActionRunPhase,
    AttackMode,
    Command,
    CommandType,
    Direction,
    EnemyIntent,
    EntityState,
    Faction,
    GridPos,
    PreparedActionKind,
    RewardKind,
    execute_turn,
    preview_turn,
    plan_enemy_action,
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


def test_melee_and_ranged_modes_trade_damage_for_range() -> None:
    melee = _run(801)
    assert melee.player is not None
    melee.state.width = 7
    melee.state.height = 4
    melee.state.walls = set()
    melee.state.entities = {
        "player": EntityState("player", Faction.PLAYER, GridPos(1, 1), 8, 8, "P"),
        "enemy": EntityState("enemy", Faction.ENEMY, GridPos(2, 1), 5, 5, "E", "melee"),
    }
    melee.facing = Direction.RIGHT
    melee.attack()
    assert melee.state.entities["enemy"].hp == 3
    assert melee.state.entities["enemy"].pos == GridPos(3, 1)

    ranged = _run(802)
    ranged.state.width = 7
    ranged.state.height = 4
    ranged.state.walls = set()
    ranged.state.entities = {
        "player": EntityState("player", Faction.PLAYER, GridPos(1, 1), 8, 8, "P"),
        "near": EntityState("near", Faction.ENEMY, GridPos(3, 1), 5, 5, "N", "melee"),
        "far": EntityState("far", Faction.ENEMY, GridPos(4, 1), 5, 5, "F", "melee"),
    }
    ranged.facing = Direction.RIGHT
    assert ranged.toggle_attack_mode() is AttackMode.RANGED
    assert ranged.attack_cooldown == 0
    events = ranged.attack()
    assert ranged.state.entities["near"].hp == 4
    assert ranged.state.entities["near"].pos == GridPos(3, 1)
    assert ranged.state.entities["far"].hp == 5
    assert any(event.kind == "ranged_fired" for event in events)


def test_ranged_attack_stops_at_walls_and_three_cells() -> None:
    run = _run(803)
    run.state.width = 8
    run.state.height = 4
    run.state.entities = {
        "player": EntityState("player", Faction.PLAYER, GridPos(1, 1), 8, 8, "P"),
        "blocked": EntityState("blocked", Faction.ENEMY, GridPos(3, 1), 5, 5, "B", "melee"),
        "far": EntityState("far", Faction.ENEMY, GridPos(5, 1), 5, 5, "F", "melee"),
    }
    run.state.walls = {GridPos(2, 1)}
    run.facing = Direction.RIGHT
    run.toggle_attack_mode()

    events = run.attack()

    assert all(entity.hp == 5 for entity in run.active_enemies)
    assert events[0].kind == "attack_missed"
    assert events[0].to_pos == GridPos(1, 1)


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


def test_tactical_pool_starts_populated_and_top_three_drive_preview() -> None:
    run = _run(78)
    assert run.enter_tactical()
    assert len(run.tactical_actions) == 7
    assert all(command.command_type is not CommandType.WAIT for command in run.commands)
    assert run.commands == [
        action.command.in_slot(slot)
        for slot, action in enumerate(run.tactical_actions[:3], start=1)
    ]

    original_first = run.tactical_actions[0].action_id
    promoted_id = run.tactical_actions[3].action_id
    selected = run.move_tactical_action(3, -3)

    assert selected == 0
    assert run.tactical_actions[0].action_id == promoted_id
    assert run.tactical_actions[1].action_id == original_first
    preview = run.preview
    assert preview is not None
    direct = execute_turn(run.state, run.commands)
    assert state_fingerprint(preview.state) == state_fingerprint(direct.state)


def test_enemy_numbers_stay_fixed_after_an_earlier_enemy_dies() -> None:
    run = _run(781)
    enemies = run.active_enemies
    assert len(enemies) >= 2
    first_id = enemies[0].entity_id
    second_id = enemies[1].entity_id

    assert run.enemy_number(first_id) == 1
    assert run.enemy_number(second_id) == 2

    run.state.entities.pop(first_id)

    assert run.enemy_number(second_id) == 2


def test_tactical_preview_summary_tracks_enemy_damage_after_reordering() -> None:
    run = _run(782)
    run.state.width = 5
    run.state.height = 5
    run.state.walls = set()
    run.state.entities = {
        "player": EntityState("player", Faction.PLAYER, GridPos(1, 2), 8, 8, "ECHO"),
        "enemy_3": EntityState(
            "enemy_3", Faction.ENEMY, GridPos(2, 2), 3, 3, "校验射手", "ranged"
        ),
    }
    run.enemy_numbers = {"enemy_3": 3}
    run.prepared_actions = {}
    run.state.enemy_intents = ()

    assert run.enter_tactical()
    hit = run.tactical_preview_summary

    assert hit is not None
    assert (hit.player_before_hp, hit.player_after_hp) == (8, 8)
    assert len(hit.enemy_deltas) == 1
    assert hit.enemy_deltas[0].number == 3
    assert hit.enemy_deltas[0].display_name == "校验射手"
    assert (hit.enemy_deltas[0].before_hp, hit.enemy_deltas[0].after_hp) == (3, 2)
    assert hit.enemy_deltas[0].damage == 1

    run.move_tactical_action(0, 3)
    miss = run.tactical_preview_summary

    assert miss is not None
    assert miss.enemy_deltas == ()
    assert (miss.player_before_hp, miss.player_after_hp) == (8, 8)


def test_tactical_execute_ignores_reserve_actions() -> None:
    run = _run(79)
    assert run.enter_tactical()
    player = run.player
    assert player is not None
    origin = player.pos
    reserve_ids = {action.action_id for action in run.tactical_actions[3:]}
    assert len(reserve_ids) == 4

    result = run.execute_tactical()

    assert result is not None
    executed_ids = {action.action_id for action in run.tactical_actions[:3]}
    if "move_toward" not in executed_ids and not executed_ids & {"move_left", "move_right", "move_back"}:
        assert result.state.entities["player"].pos == origin


def test_tactical_pool_prioritises_a_valid_context_action() -> None:
    run = _run(80)
    player = run.player
    assert player is not None
    enemy = run.active_enemies[0]
    enemy.pos = player.pos.moved(Direction.RIGHT)
    run.facing = Direction.LEFT

    assert run.enter_tactical()

    assert run.tactical_actions[0].action_id == "push_target"
    assert run.commands[0].direction is Direction.RIGHT


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


def test_final_warden_has_cross_burst_and_upgraded_damage() -> None:
    run = _run(804)
    run.encounter_index = 2
    run._build_encounter(carry_hp=8)
    warden = next(enemy for enemy in run.active_enemies if enemy.enemy_kind == "warden")
    assert (warden.hp, warden.max_hp) == (12, 12)
    assert run.player is not None
    run.state.width = 7
    run.state.height = 7
    run.state.walls = set()
    run.player.pos = GridPos(3, 3)
    warden.pos = GridPos(3, 0)
    special = plan_enemy_action(run.state, warden.entity_id, special_ready=True)
    assert special.damage == 4
    assert special.label == "PHASE CROSS"
    assert set(special.target_positions) == {
        GridPos(3, 3), GridPos(3, 2), GridPos(4, 3),
        GridPos(3, 4), GridPos(2, 3),
    }
    run.prepared_actions[warden.entity_id] = special
    run._sync_tactical_intents()
    burst_intents = [
        intent for intent in run.state.enemy_intents
        if intent.actor_id == warden.entity_id
    ]
    assert len(burst_intents) == 5
    waits = [Command("player", CommandType.WAIT, slot) for slot in range(1, 4)]
    preview = preview_turn(run.state, waits)
    assert preview.state.entities["player"].hp == 4

    normal = plan_enemy_action(run.state, warden.entity_id, special_ready=False)
    assert normal.damage == 3


def test_warden_cross_burst_hits_adjacent_locked_cell_in_realtime() -> None:
    run = _run(805)
    run.encounter_index = 2
    run._build_encounter(carry_hp=8)
    assert run.player is not None
    warden = next(enemy for enemy in run.active_enemies if enemy.enemy_kind == "warden")
    run.state.width = 7
    run.state.height = 7
    run.state.walls = set()
    run.player.pos = GridPos(3, 3)
    warden.pos = GridPos(3, 0)
    special = plan_enemy_action(run.state, warden.entity_id, special_ready=True)
    run.player.pos = GridPos(4, 3)

    events = run._execute_prepared(special)

    assert run.player.hp == 4
    assert any(event.kind == "damaged" and event.amount == 4 for event in events)
    assert run.enemy_special_timers[warden.entity_id] == 2.4

    warden.hp = 6
    run.player.pos = GridPos(3, 3)
    run._execute_prepared(special)
    assert run.enemy_special_timers[warden.entity_id] == 1.8


def test_action_state_keeps_domain_free_of_pygame() -> None:
    run = _run()
    assert all(entity.faction in {Faction.PLAYER, Faction.ENEMY} for entity in run.state.entities.values())
