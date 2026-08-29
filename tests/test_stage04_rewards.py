from __future__ import annotations

import random

import pytest

from src.domain import (
    Command,
    CommandType,
    CombatState,
    Direction,
    EnemyIntent,
    EntityState,
    Faction,
    GridPos,
    PluginDefinition,
    RewardPool,
    simulate_turn,
)
from src.domain.level import LevelPhase, LevelRun
from src.infrastructure import load_level_one


def _candidate_ids(seed: int) -> tuple[str, ...]:
    level, plugins = load_level_one()
    run = LevelRun(level, plugins, seed)
    run.encounter.state.entities.pop("charger_alpha")
    run._settle_victory()
    first = tuple(item.plugin_id for item in run.reward_choices)
    run.choose_reward("echo_protocol")
    run.encounter.state.entities.pop("guard_beta")
    run._settle_victory()
    second = tuple(item.plugin_id for item in run.reward_choices)
    return first + second


def test_fixed_seed_reproduces_candidates_and_different_seeds_vary() -> None:
    assert _candidate_ids(17) == _candidate_ids(17)
    sequences = {_candidate_ids(seed) for seed in range(10, 20)}
    assert len(sequences) > 1


def test_reward_candidates_have_no_duplicate_and_unselected_do_not_apply() -> None:
    level, plugins = load_level_one()
    run = LevelRun(level, plugins, 10303)
    run.encounter.state.entities.pop("charger_alpha")
    run._settle_victory()
    offered = run.reward_choices
    assert len(offered) == len({item.plugin_id for item in offered}) == 3
    selected = offered[0].plugin_id
    not_selected = {item.plugin_id for item in offered[1:]}
    run.choose_reward(selected)
    assert run.player_build == {selected: 1}
    assert not not_selected.intersection(run.player_build)


def test_requirements_conflicts_and_max_stack_are_filtered() -> None:
    definitions = {
        "base": PluginDefinition("base", "Base", "Base", "shield_plus_one"),
        "upgrade": PluginDefinition(
            "upgrade", "Upgrade", "Upgrade", "echo_grants_shield", requirements=("base",)
        ),
        "conflict": PluginDefinition(
            "conflict", "Conflict", "Conflict", "push_damage_plus_one", conflicts=("base",)
        ),
        "stack": PluginDefinition(
            "stack", "Stack", "Stack", "push_damage_plus_one", max_stack=2
        ),
    }
    pool = RewardPool(definitions, random.Random(7))
    assert {item.plugin_id for item in pool.candidates(tuple(definitions), 2, {})} <= {
        "base", "conflict", "stack"
    }
    eligible = pool.candidates(tuple(definitions), 2, {"base": 1, "stack": 1})
    assert {item.plugin_id for item in eligible} == {"upgrade", "stack"}
    with pytest.raises(ValueError, match="eligible"):
        pool.candidates(tuple(definitions), 2, {"base": 1, "stack": 2})


def test_second_reward_saves_build_into_climax_and_restart_resets_it() -> None:
    level, plugins = load_level_one()
    run = LevelRun(level, plugins, 10303)
    run.encounter.state.entities.pop("charger_alpha")
    run._settle_victory()
    run.choose_reward("echo_protocol")
    run.encounter.state.entities.pop("guard_beta")
    run._settle_victory()
    assert run.phase is LevelPhase.REWARD
    second = run.reward_choices[0].plugin_id
    run.choose_reward(second)
    assert run.progress == (3, 3)
    assert run.encounter.state.player_plugins == ("echo_protocol", second)
    run.restart(10303)
    assert run.player_build == {}
    assert run.encounter.state.player_plugins == ()


def _strategy_state(*effects: str) -> CombatState:
    return CombatState(
        6,
        3,
        {
            "player": EntityState("player", Faction.PLAYER, GridPos(0, 1), 5, 5, "P"),
            "enemy": EntityState("enemy", Faction.ENEMY, GridPos(1, 1), 2, 2, "E", "guard"),
        },
        enemy_intents=(EnemyIntent("enemy", GridPos(0, 1), 1, 1),),
        player_plugin_effects=effects,
    )


def test_three_builds_change_strategy_in_the_same_combat_state() -> None:
    echo = simulate_turn(
        _strategy_state("repeat_first_on_empty_third"),
        [
            Command("player", CommandType.PUSH, 1, Direction.RIGHT),
            Command("player", CommandType.MOVE, 2, Direction.RIGHT),
        ],
    )
    kinetic = simulate_turn(
        _strategy_state("push_damage_plus_one"),
        [
            Command("player", CommandType.PUSH, 1, Direction.RIGHT),
            Command("player", CommandType.MOVE, 2, Direction.DOWN),
            Command("player", CommandType.WAIT, 3),
        ],
    )
    control = simulate_turn(
        _strategy_state("pull_range_plus_one", "pull_cancels_intent"),
        [
            Command("player", CommandType.PUSH, 1, Direction.RIGHT),
            Command("player", CommandType.PULL, 2, target_entity_id="enemy"),
        ],
    )
    assert "enemy" not in echo.state.entities
    assert "enemy" not in kinetic.state.entities
    assert "enemy" in control.state.entities
    assert control.state.entities["player"].hp == 5
    assert any(event.detail == "tractor_lock" for event in control.events)


def test_build_synergies_change_command_order_and_collision_result() -> None:
    shield_then_push = simulate_turn(
        CombatState(
            4,
            2,
            {
                "player": EntityState("player", Faction.PLAYER, GridPos(0, 0), 5, 5, "P"),
                "enemy": EntityState("enemy", Faction.ENEMY, GridPos(1, 0), 2, 2, "E"),
            },
            player_plugin_effects=("shield_primes_push",),
        ),
        [
            Command("player", CommandType.SHIELD, 1),
            Command("player", CommandType.PUSH, 2, Direction.RIGHT),
        ],
    )
    collision = simulate_turn(
        CombatState(
            3,
            2,
            {
                "player": EntityState("player", Faction.PLAYER, GridPos(0, 0), 5, 5, "P"),
                "enemy": EntityState("enemy", Faction.ENEMY, GridPos(1, 0), 3, 3, "E"),
            },
            walls={GridPos(2, 0)},
            player_plugin_effects=("push_damage_plus_one", "collision_damage_plus_one"),
        ),
        [Command("player", CommandType.PUSH, 1, Direction.RIGHT)],
    )
    assert "enemy" not in shield_then_push.state.entities
    assert "enemy" not in collision.state.entities
