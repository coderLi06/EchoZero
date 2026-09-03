"""Pure action-Roguelike run state with tactical access to the shared simulator."""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from .behavior_tree import PreparedAction, PreparedActionKind, plan_enemy_action
from .content import PluginDefinition
from .model import (
    Command,
    CommandType,
    CombatState,
    Direction,
    EnemyIntent,
    EntityState,
    Faction,
    GridPos,
    LogicEvent,
    SimulationResult,
    TimelineRule,
)
from .procedural import ProceduralEncounter, ProceduralEncounterGenerator
from .simulation import execute_turn, preview_turn


class ActionRunPhase(str, Enum):
    ACTION = "action"
    TACTICAL = "tactical"
    REWARD = "reward"
    VICTORY = "victory"
    DEFEAT = "defeat"


class RewardKind(str, Enum):
    PROTOCOL = "protocol"
    SKILL = "skill"
    STAT = "stat"


class AttackMode(str, Enum):
    MELEE = "melee"
    RANGED = "ranged"


@dataclass(frozen=True)
class ActionReward:
    reward_id: str
    kind: RewardKind
    display_name: str
    description: str
    protocol_id: str = ""


@dataclass(frozen=True)
class TacticalAction:
    action_id: str
    display_name: str
    command: Command


@dataclass(frozen=True)
class TacticalEnemyDelta:
    entity_id: str
    number: int
    display_name: str
    before_hp: int
    after_hp: int
    damage: int


@dataclass(frozen=True)
class TacticalPreviewSummary:
    player_before_hp: int
    player_after_hp: int
    player_max_hp: int
    enemy_deltas: tuple[TacticalEnemyDelta, ...]


UPGRADE_REWARDS = (
    ActionReward("attack_plus", RewardKind.STAT, "锋刃校准", "基础攻击伤害 +1。"),
    ActionReward("core_plus", RewardKind.STAT, "核心扩容", "最大 CORE +2，并恢复 2。"),
    ActionReward("attack_speed", RewardKind.SKILL, "脉冲加速", "基础攻击冷却缩短 15%。"),
    ActionReward("dodge_flow", RewardKind.SKILL, "闪避回路", "闪避冷却缩短 0.25 秒。"),
    ActionReward("tractor_power", RewardKind.SKILL, "牵引增幅", "牵引脉冲伤害 +1。"),
)


class ActionRun:
    ENCOUNTER_COUNT = 3
    TACTICAL_COOLDOWN = 5.0
    ENCOUNTER_GRACE = 1.65

    def __init__(
        self,
        seed: int,
        plugins: Mapping[str, PluginDefinition],
        generator: ProceduralEncounterGenerator | None = None,
        meta_core_bonus: int = 0,
    ) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self.plugins = dict(plugins)
        self.generator = generator or ProceduralEncounterGenerator()
        self.meta_core_bonus = max(0, meta_core_bonus)
        self.encounter_index = 0
        self.build: dict[str, int] = {}
        self.attack_damage = 2
        self.attack_mode = AttackMode.MELEE
        self.max_core_bonus = 0
        self.attack_cooldown_base = 0.34
        self.dodge_cooldown_base = 1.35
        self.skill_damage = 1
        self.attack_cooldown = 0.0
        self.dodge_cooldown = 0.0
        self.skill_cooldown = 0.0
        self.tactical_cooldown = 0.0
        self.invulnerable = 0.0
        self.overclock = 0.0
        self.hit_stop = 0.0
        self.elapsed = 0.0
        self.encounter_elapsed = 0.0
        self.action_serial = 0
        self.phase = ActionRunPhase.ACTION
        self.commands = [
            Command("player", CommandType.WAIT, slot) for slot in range(1, 4)
        ]
        self.tactical_actions: list[TacticalAction] = []
        self.enemy_numbers: dict[str, int] = {}
        self.prepared_actions: dict[str, PreparedAction] = {}
        self.enemy_timers: dict[str, float] = {}
        self.enemy_special_timers: dict[str, float] = {}
        self.reward_choices: tuple[ActionReward, ...] = ()
        self.last_events: tuple[LogicEvent, ...] = ()
        self.last_tactical_result: SimulationResult | None = None
        self.facing = Direction.RIGHT
        self.map: ProceduralEncounter
        self.state: CombatState
        self._build_encounter(carry_hp=None)

    @property
    def player(self) -> EntityState | None:
        return self.state.entities.get("player")

    @property
    def active_enemies(self) -> tuple[EntityState, ...]:
        return tuple(
            sorted(
                (
                    entity
                    for entity in self.state.entities.values()
                    if entity.faction is Faction.ENEMY
                ),
                key=lambda entity: entity.entity_id,
            )
        )

    @property
    def build_summary(self) -> str:
        names = [
            self.plugins[plugin_id].display_name
            for plugin_id, stacks in self.build.items()
            if stacks > 0 and plugin_id in self.plugins
            for _ in range(stacks)
        ]
        return " / ".join(names) if names else "未安装 Protocol"

    @property
    def tactical_ready(self) -> bool:
        return (
            self.phase is ActionRunPhase.ACTION
            and self.tactical_cooldown <= 0
            and self.player is not None
        )

    @property
    def preview(self) -> SimulationResult | None:
        if self.phase is not ActionRunPhase.TACTICAL:
            return None
        return preview_turn(self.state, self.commands)

    @property
    def tactical_preview_summary(self) -> TacticalPreviewSummary | None:
        result = self.preview
        player = self.player
        if result is None or player is None:
            return None
        preview_player = result.state.entities.get(player.entity_id)
        after_hp = preview_player.hp if preview_player is not None else 0
        deltas: list[TacticalEnemyDelta] = []
        for enemy in sorted(self.active_enemies, key=lambda item: self.enemy_number(item.entity_id)):
            preview_enemy = result.state.entities.get(enemy.entity_id)
            enemy_after_hp = preview_enemy.hp if preview_enemy is not None else 0
            damage = max(0, enemy.hp - enemy_after_hp)
            if damage <= 0:
                continue
            deltas.append(
                TacticalEnemyDelta(
                    enemy.entity_id,
                    self.enemy_number(enemy.entity_id),
                    enemy.display_name,
                    enemy.hp,
                    enemy_after_hp,
                    damage,
                )
            )
        return TacticalPreviewSummary(
            player.hp, after_hp, player.max_hp, tuple(deltas)
        )

    def enemy_number(self, entity_id: str) -> int:
        """Return the stable encounter-local number shown in every combat view."""
        known = self.enemy_numbers.get(entity_id)
        if known is not None:
            return known
        active_ids = sorted(enemy.entity_id for enemy in self.active_enemies)
        return active_ids.index(entity_id) + 1 if entity_id in active_ids else 0

    def update(self, dt: float) -> tuple[LogicEvent, ...]:
        dt = max(0.0, min(dt, 0.1))
        if self.phase is not ActionRunPhase.ACTION:
            return ()
        self.elapsed += dt
        self.encounter_elapsed += dt
        self.attack_cooldown = max(0.0, self.attack_cooldown - dt)
        self.dodge_cooldown = max(0.0, self.dodge_cooldown - dt)
        self.skill_cooldown = max(0.0, self.skill_cooldown - dt)
        self.tactical_cooldown = max(0.0, self.tactical_cooldown - dt)
        self.invulnerable = max(0.0, self.invulnerable - dt)
        self.overclock = max(0.0, self.overclock - dt)
        if self.hit_stop > 0:
            self.hit_stop = max(0.0, self.hit_stop - dt)
            return ()

        events: list[LogicEvent] = []
        for enemy in self.active_enemies:
            self.enemy_timers[enemy.entity_id] = self.enemy_timers.get(enemy.entity_id, 0.0) - dt
            self.enemy_special_timers[enemy.entity_id] = max(
                0.0, self.enemy_special_timers.get(enemy.entity_id, 0.0) - dt
            )
            if enemy.entity_id not in self.prepared_actions:
                self._prepare_action(enemy.entity_id)
            if self.enemy_timers[enemy.entity_id] <= 0:
                prepared = self.prepared_actions.get(enemy.entity_id)
                if prepared is not None:
                    events.extend(self._execute_prepared(prepared))
                if enemy.entity_id in self.state.entities:
                    self._prepare_action(enemy.entity_id)
                    self.enemy_timers[enemy.entity_id] = self._enemy_interval(enemy.enemy_kind)
        return self._finish_action(events)

    def move_player(self, direction: Direction) -> tuple[LogicEvent, ...]:
        if self.phase is not ActionRunPhase.ACTION or self.player is None or self.hit_stop > 0:
            return ()
        self.facing = direction
        destination = self.player.pos.moved(direction)
        if self._blocked(destination):
            return self._remember((LogicEvent("move_blocked", 0, "player", to_pos=destination),))
        origin = self.player.pos
        self.player.pos = destination
        events = [LogicEvent("moved", 0, "player", from_pos=origin, to_pos=destination)]
        events.extend(self._apply_hazard(self.player))
        return self._finish_action(events)

    def attack(self, direction: Direction | None = None) -> tuple[LogicEvent, ...]:
        if (
            self.phase is not ActionRunPhase.ACTION
            or self.player is None
            or self.attack_cooldown > 0
            or self.hit_stop > 0
        ):
            return ()
        self.facing = direction or self.facing
        self.action_serial += 1
        haste = 0.70 if self.overclock > 0 else 1.0
        self.attack_cooldown = self.attack_cooldown_base * haste
        damage = self.attack_damage + self._effect_count("push_damage_plus_one")
        if "shield_primes_push" in self._effects() and self.invulnerable > 0:
            damage += 1
        if self.attack_mode is AttackMode.RANGED:
            target, endpoint = self._first_ranged_target(3)
            if target is None:
                return self._remember(
                    (
                        LogicEvent(
                            "attack_missed", 0, "player",
                            from_pos=self.player.pos, to_pos=endpoint,
                            detail="ranged_attack",
                        ),
                    )
                )
            damage = max(1, damage // 2)
            events = [
                LogicEvent(
                    "ranged_fired", 0, "player", target.entity_id,
                    from_pos=self.player.pos, to_pos=target.pos,
                    amount=damage, detail="ranged_attack",
                )
            ]
            events.extend(self._damage(target, damage, "ranged_attack"))
            self.hit_stop = 0.035
            return self._finish_action(events)
        target = self.state.entity_at(self.player.pos.moved(self.facing))
        if target is None or target.faction is not Faction.ENEMY:
            return self._remember(
                (LogicEvent("attack_missed", 0, "player", to_pos=self.player.pos.moved(self.facing)),)
            )
        events = list(self._damage(target, damage, "basic_attack"))
        if target.entity_id in self.state.entities:
            events.extend(self._knockback(target, self.facing, "basic_attack"))
        self.hit_stop = 0.055
        if self.action_serial % 3 == 0 and "repeat_first_on_empty_third" in self._effects():
            self.attack_cooldown *= 0.55
            events.append(LogicEvent("plugin_triggered", 0, "player", detail="echo_protocol"))
        return self._finish_action(events)

    def toggle_attack_mode(self) -> AttackMode:
        if self.phase is ActionRunPhase.ACTION:
            self.attack_mode = (
                AttackMode.RANGED
                if self.attack_mode is AttackMode.MELEE
                else AttackMode.MELEE
            )
            self.last_events = (
                LogicEvent(
                    "attack_mode_changed", 0, "player", detail=self.attack_mode.value
                ),
            )
        return self.attack_mode

    def dodge(self, direction: Direction) -> tuple[LogicEvent, ...]:
        if (
            self.phase is not ActionRunPhase.ACTION
            or self.player is None
            or self.dodge_cooldown > 0
        ):
            return ()
        self.facing = direction
        self.dodge_cooldown = self.dodge_cooldown_base
        self.invulnerable = 0.24
        origin = self.player.pos
        for _ in range(2):
            destination = self.player.pos.moved(direction)
            if self._blocked(destination):
                break
            self.player.pos = destination
        events: list[LogicEvent] = [
            LogicEvent("dodged", 0, "player", from_pos=origin, to_pos=self.player.pos)
        ]
        if "shield_plus_one" in self._effects():
            self.player.shield += 1
            events.append(LogicEvent("shielded", 0, "player", amount=1, detail="emergency_barrier"))
        events.extend(self._apply_hazard(self.player))
        return self._finish_action(events)

    def tractor_skill(self, direction: Direction | None = None) -> tuple[LogicEvent, ...]:
        if (
            self.phase is not ActionRunPhase.ACTION
            or self.player is None
            or self.skill_cooldown > 0
        ):
            return ()
        self.facing = direction or self.facing
        self.skill_cooldown = 2.2
        pull_range = 3 + (1 if "pull_range_plus_one" in self._effects() else 0)
        targets = [
            enemy
            for enemy in self.active_enemies
            if self._in_direction(enemy.pos, self.facing)
            and enemy.pos.manhattan_distance(self.player.pos) <= pull_range
        ]
        if not targets:
            return self._remember((LogicEvent("pull_missed", 0, "player"),))
        target = min(targets, key=lambda enemy: enemy.pos.manhattan_distance(self.player.pos))
        events = list(self._damage(target, self.skill_damage, "tractor_skill"))
        if target.entity_id in self.state.entities:
            destination = target.pos.moved(self._opposite(self.facing))
            if not self._blocked(destination):
                origin = target.pos
                target.pos = destination
                events.append(
                    LogicEvent("pulled", 0, "player", target.entity_id, origin, destination)
                )
            if "pull_cancels_intent" in self._effects():
                self.enemy_timers[target.entity_id] = max(
                    self.enemy_timers.get(target.entity_id, 0.0), 0.8
                )
                events.append(
                    LogicEvent("intent_cancelled", 0, target.entity_id, detail="tractor_lock")
                )
        self.hit_stop = 0.07
        return self._finish_action(events)

    def enter_tactical(self) -> bool:
        if not self.tactical_ready:
            return False
        self.phase = ActionRunPhase.TACTICAL
        self.tactical_actions = self._build_tactical_actions()
        self._sync_tactical_commands()
        self._sync_tactical_intents()
        return True

    def cancel_tactical(self) -> None:
        if self.phase is ActionRunPhase.TACTICAL:
            self.phase = ActionRunPhase.ACTION
            self.state.enemy_intents = ()

    def set_tactical_command(self, slot: int, command: Command) -> None:
        if self.phase is not ActionRunPhase.TACTICAL or not 1 <= slot <= 3:
            return
        self.commands[slot - 1] = command.in_slot(slot)

    def move_tactical_action(self, index: int, offset: int) -> int:
        if self.phase is not ActionRunPhase.TACTICAL or not self.tactical_actions:
            return index
        destination = max(0, min(len(self.tactical_actions) - 1, index + offset))
        if destination == index:
            return index
        action = self.tactical_actions.pop(index)
        self.tactical_actions.insert(destination, action)
        self._sync_tactical_commands()
        return destination

    def execute_tactical(self) -> SimulationResult | None:
        if self.phase is not ActionRunPhase.TACTICAL:
            return None
        result = execute_turn(self.state, self.commands)
        self.state = result.state.clone()
        self.last_tactical_result = result
        self.last_events = result.events
        self.tactical_cooldown = self.TACTICAL_COOLDOWN
        self.overclock = 2.2 if "repeat_first_on_empty_third" in self._effects() else 0.8
        self.phase = ActionRunPhase.ACTION
        self.state.enemy_intents = ()
        self._remove_dead_ai()
        self._check_outcome()
        return result

    def choose_reward(self, index: int) -> ActionReward:
        if self.phase is not ActionRunPhase.REWARD:
            raise ValueError("No reward is available")
        reward = self.reward_choices[index]
        player = self.player
        if reward.kind is RewardKind.PROTOCOL:
            self.build[reward.protocol_id] = self.build.get(reward.protocol_id, 0) + 1
        elif reward.reward_id == "attack_plus":
            self.attack_damage += 1
        elif reward.reward_id == "core_plus" and player is not None:
            self.max_core_bonus += 2
            player.max_hp += 2
            player.hp = min(player.max_hp, player.hp + 2)
        elif reward.reward_id == "attack_speed":
            self.attack_cooldown_base = max(0.18, self.attack_cooldown_base * 0.85)
        elif reward.reward_id == "dodge_flow":
            self.dodge_cooldown_base = max(0.65, self.dodge_cooldown_base - 0.25)
        elif reward.reward_id == "tractor_power":
            self.skill_damage += 1
        carry_hp = player.hp if player is not None else None
        self.encounter_index += 1
        self._build_encounter(carry_hp)
        return reward

    def _build_encounter(self, carry_hp: int | None) -> None:
        self.map = self.generator.generate(self.seed, self.encounter_index)
        max_hp = 8 + self.meta_core_bonus + self.max_core_bonus
        player_hp = max_hp if carry_hp is None else min(max_hp, max(1, carry_hp))
        entities: dict[str, EntityState] = {
            "player": EntityState(
                "player", Faction.PLAYER, self.map.player_spawn,
                player_hp, max_hp, "ECHO ZERO"
            )
        }
        for spawn in self.map.enemies:
            display = {
                "melee": "追猎体",
                "charger": "突进体",
                "ranged": "校验射手",
                "warden": "相位守卫",
            }[spawn.enemy_kind]
            entities[spawn.entity_id] = EntityState(
                spawn.entity_id, Faction.ENEMY, spawn.pos,
                spawn.hp, spawn.hp, display, spawn.enemy_kind
            )
        self.enemy_numbers = {
            spawn.entity_id: index
            for index, spawn in enumerate(self.map.enemies, start=1)
        }
        effects = tuple(
            self.plugins[plugin_id].effect_type
            for plugin_id, stacks in self.build.items()
            if plugin_id in self.plugins
            for _ in range(stacks)
        )
        rules = (
            (TimelineRule.STABLE, TimelineRule.REVERSE)
            if self.encounter_index >= 1
            else (TimelineRule.STABLE,)
        )
        self.state = CombatState(
            self.map.width,
            self.map.height,
            entities,
            set(self.map.walls),
            player_plugins=tuple(self.build),
            player_plugin_effects=effects,
            timeline_rules=rules,
            rule_nodes=frozenset({self.map.reward_pos}),
        )
        self.phase = ActionRunPhase.ACTION
        self.encounter_elapsed = 0.0
        self.prepared_actions.clear()
        self.enemy_timers = {
            enemy.entity_id: self.ENCOUNTER_GRACE + index * 0.18
            for index, enemy in enumerate(self.active_enemies)
        }
        self.enemy_special_timers = {
            enemy.entity_id: 1.8 + index * 0.4
            for index, enemy in enumerate(self.active_enemies)
        }
        for enemy in self.active_enemies:
            self._prepare_action(enemy.entity_id)
        self.last_events = ()

    def _prepare_action(self, enemy_id: str) -> None:
        if enemy_id not in self.state.entities or self.player is None:
            return
        ready = self.enemy_special_timers.get(enemy_id, 0.0) <= 0
        self.prepared_actions[enemy_id] = plan_enemy_action(
            self.state, enemy_id, special_ready=ready
        )

    def _execute_prepared(self, prepared: PreparedAction) -> tuple[LogicEvent, ...]:
        actor = self.state.entities.get(prepared.actor_id)
        player = self.player
        if actor is None or player is None:
            return ()
        if prepared.kind in {
            PreparedActionKind.CHASE,
            PreparedActionKind.RETREAT,
            PreparedActionKind.STRAFE,
            PreparedActionKind.PATROL,
        }:
            if not self._blocked(prepared.target_pos, ignore_id=actor.entity_id):
                origin = actor.pos
                actor.pos = prepared.target_pos
                return (
                    LogicEvent(
                        "enemy_moved", 0, actor.entity_id,
                        from_pos=origin, to_pos=actor.pos, detail=prepared.label
                    ),
                )
            return ()
        if prepared.kind is PreparedActionKind.SPECIAL:
            self.enemy_special_timers[actor.entity_id] = (
                1.8
                if actor.enemy_kind == "warden" and actor.hp <= actor.max_hp // 2
                else 2.4 if actor.enemy_kind == "warden" else 3.2
            )
            if actor.enemy_kind == "charger":
                return self._execute_charge(actor, player, prepared)
            if actor.enemy_kind == "warden":
                targets = prepared.target_positions or (prepared.target_pos,)
                if player.pos not in targets:
                    return (
                        LogicEvent(
                            "attack_missed", 0, actor.entity_id,
                            to_pos=prepared.target_pos, detail=prepared.label,
                        ),
                    )
                return self._damage_player(
                    prepared.damage, actor.entity_id, prepared.label
                )
        if player.pos != prepared.target_pos:
            return (
                LogicEvent(
                    "attack_missed", 0, actor.entity_id,
                    to_pos=prepared.target_pos, detail=prepared.label
                ),
            )
        return self._damage_player(prepared.damage, actor.entity_id, prepared.label)

    def _execute_charge(
        self, actor: EntityState, player: EntityState, prepared: PreparedAction
    ) -> tuple[LogicEvent, ...]:
        direction = self._direction_toward(actor.pos, prepared.target_pos)
        if direction is None:
            return ()
        origin = actor.pos
        while actor.pos.manhattan_distance(prepared.target_pos) > 1:
            destination = actor.pos.moved(direction)
            if self._blocked(destination, ignore_id=actor.entity_id):
                break
            actor.pos = destination
        events = [
            LogicEvent(
                "enemy_charged", 0, actor.entity_id,
                from_pos=origin, to_pos=actor.pos, detail=prepared.label
            )
        ]
        if actor.pos.manhattan_distance(player.pos) == 1:
            events.extend(self._damage_player(prepared.damage, actor.entity_id, prepared.label))
        return tuple(events)

    def _sync_tactical_intents(self) -> None:
        intents: list[EnemyIntent] = []
        next_order = 1
        for enemy in self.active_enemies:
            prepared = self.prepared_actions.get(enemy.entity_id)
            if prepared is None:
                self._prepare_action(enemy.entity_id)
                prepared = self.prepared_actions[enemy.entity_id]
            is_move = prepared.kind in {
                PreparedActionKind.CHASE,
                PreparedActionKind.RETREAT,
                PreparedActionKind.STRAFE,
                PreparedActionKind.PATROL,
            }
            targets = prepared.target_positions or (prepared.target_pos,)
            for target in targets:
                intents.append(
                    EnemyIntent(
                        enemy.entity_id,
                        target,
                        prepared.damage,
                        next_order,
                        "move" if is_move else "attack",
                        prepared.label,
                    )
                )
                next_order += 1
        self.state.enemy_intents = tuple(intents)

    def _first_ranged_target(
        self, attack_range: int
    ) -> tuple[EntityState | None, GridPos]:
        player = self.player
        if player is None:
            return (None, GridPos(0, 0))
        endpoint = player.pos
        for _ in range(attack_range):
            candidate = endpoint.moved(self.facing)
            if not self.state.in_bounds(candidate) or candidate in self.state.walls:
                break
            endpoint = candidate
            target = self.state.entity_at(candidate)
            if target is not None:
                return (
                    target if target.faction is Faction.ENEMY else None,
                    endpoint,
                )
        return (None, endpoint)

    def _build_tactical_actions(self) -> list[TacticalAction]:
        player = self.player
        if player is None:
            return []
        left = {
            Direction.UP: Direction.LEFT,
            Direction.LEFT: Direction.DOWN,
            Direction.DOWN: Direction.RIGHT,
            Direction.RIGHT: Direction.UP,
        }[self.facing]
        right = self._opposite(left)
        back = self._opposite(self.facing)
        nearest = min(
            self.active_enemies,
            key=lambda enemy: (enemy.pos.manhattan_distance(player.pos), enemy.entity_id),
            default=None,
        )
        pull_range = 2 + (1 if "pull_range_plus_one" in self._effects() else 0)
        aligned = [
            enemy for enemy in self.active_enemies
            if (enemy.pos.x == player.pos.x or enemy.pos.y == player.pos.y)
            and enemy.pos.manhattan_distance(player.pos) <= pull_range
        ]
        pull_target = min(
            aligned,
            key=lambda enemy: (enemy.pos.manhattan_distance(player.pos), enemy.entity_id),
            default=nearest,
        )
        toward = self.facing
        if nearest is not None:
            dx = nearest.pos.x - player.pos.x
            dy = nearest.pos.y - player.pos.y
            if abs(dx) >= abs(dy) and dx:
                toward = Direction.RIGHT if dx > 0 else Direction.LEFT
            elif dy:
                toward = Direction.DOWN if dy > 0 else Direction.UP
        adjacent = nearest is not None and nearest.pos.manhattan_distance(player.pos) == 1
        push = TacticalAction(
            "push_target", "威胁推击",
            Command("player", CommandType.PUSH, 1, toward),
        )
        pull = TacticalAction(
            "pull_target", f"牵引 · {pull_target.display_name if pull_target else '无目标'}",
            Command(
                "player", CommandType.PULL, 2,
                target_entity_id=pull_target.entity_id if pull_target else None,
            ),
        )
        shield = TacticalAction(
            "raise_shield", "展开护盾",
            Command("player", CommandType.SHIELD, 3),
        )
        approach = TacticalAction(
            "move_toward", "接近威胁",
            Command("player", CommandType.MOVE, 4, toward),
        )
        flank = [
            TacticalAction(
                "move_left", "向左侧移",
                Command("player", CommandType.MOVE, 5, left),
            ),
            TacticalAction(
                "move_right", "向右侧移",
                Command("player", CommandType.MOVE, 6, right),
            ),
            TacticalAction(
                "move_back", "向后撤离",
                Command("player", CommandType.MOVE, 7, back),
            ),
        ]
        if adjacent:
            return [push, shield, flank[2], pull, approach, flank[0], flank[1]]
        if aligned:
            return [pull, shield, approach, push, flank[0], flank[1], flank[2]]
        return [approach, shield, flank[0], flank[1], push, pull, flank[2]]

    def _sync_tactical_commands(self) -> None:
        selected = self.tactical_actions[:3]
        self.commands = [
            action.command.in_slot(slot)
            for slot, action in enumerate(selected, start=1)
        ]
        while len(self.commands) < 3:
            self.commands.append(
                Command("player", CommandType.WAIT, len(self.commands) + 1)
            )

    def _damage(
        self, target: EntityState, amount: int, detail: str
    ) -> tuple[LogicEvent, ...]:
        absorbed = min(target.shield, amount)
        events: list[LogicEvent] = []
        if absorbed:
            target.shield -= absorbed
            amount -= absorbed
            events.append(
                LogicEvent("shield_absorbed", 0, "player", target.entity_id, amount=absorbed)
            )
        if amount <= 0:
            return tuple(events)
        target.hp -= amount
        events.append(
            LogicEvent(
                "damaged", 0, "player", target.entity_id,
                to_pos=target.pos, amount=amount, detail=detail
            )
        )
        if target.hp <= 0:
            del self.state.entities[target.entity_id]
            self.prepared_actions.pop(target.entity_id, None)
            events.append(
                LogicEvent("died", 0, "player", target.entity_id, to_pos=target.pos)
            )
        return tuple(events)

    def _damage_player(
        self, amount: int, actor_id: str, detail: str
    ) -> tuple[LogicEvent, ...]:
        player = self.player
        if player is None or self.invulnerable > 0:
            return (
                LogicEvent("attack_evaded", 0, actor_id, "player", detail=detail),
            )
        absorbed = min(player.shield, amount)
        events: list[LogicEvent] = []
        if absorbed:
            player.shield -= absorbed
            amount -= absorbed
            events.append(
                LogicEvent("shield_absorbed", 0, actor_id, "player", amount=absorbed)
            )
        if amount > 0:
            player.hp -= amount
            events.append(
                LogicEvent(
                    "damaged", 0, actor_id, "player",
                    to_pos=player.pos, amount=amount, detail=detail
                )
            )
            self.hit_stop = 0.075
            if player.hp <= 0:
                del self.state.entities["player"]
                events.append(
                    LogicEvent("died", 0, actor_id, "player", to_pos=player.pos)
                )
        return tuple(events)

    def _knockback(
        self, target: EntityState, direction: Direction, detail: str
    ) -> tuple[LogicEvent, ...]:
        destination = target.pos.moved(direction)
        if self._blocked(destination, ignore_id=target.entity_id):
            collision = 1 + self._effect_count("collision_damage_plus_one")
            return self._damage(target, collision, "collision")
        origin = target.pos
        target.pos = destination
        if "push_damage_plus_one" in self._effects():
            self.dodge_cooldown = max(0.0, self.dodge_cooldown - 0.35)
        return (
            LogicEvent(
                "pushed", 0, "player", target.entity_id,
                from_pos=origin, to_pos=destination, detail=detail
            ),
        )

    def _apply_hazard(self, entity: EntityState) -> tuple[LogicEvent, ...]:
        if entity.pos not in self.map.hazards:
            return ()
        if entity.entity_id == "player":
            return self._damage_player(1, "hazard", "danger_zone")
        return self._damage(entity, 1, "danger_zone")

    def _finish_action(self, events: list[LogicEvent] | tuple[LogicEvent, ...]) -> tuple[LogicEvent, ...]:
        result = self._remember(tuple(events))
        self._remove_dead_ai()
        self._check_outcome()
        return result

    def _remember(self, events: tuple[LogicEvent, ...]) -> tuple[LogicEvent, ...]:
        if events:
            self.last_events = events
        return events

    def _check_outcome(self) -> None:
        if self.player is None:
            self.phase = ActionRunPhase.DEFEAT
            return
        if self.active_enemies:
            return
        if self.encounter_index >= self.ENCOUNTER_COUNT - 1:
            self.phase = ActionRunPhase.VICTORY
        else:
            self.phase = ActionRunPhase.REWARD
            self.reward_choices = self._generate_rewards()

    def _generate_rewards(self) -> tuple[ActionReward, ...]:
        eligible = [
            definition
            for definition in self.plugins.values()
            if self._protocol_eligible(definition)
        ]
        protocol = self.rng.choice(eligible) if eligible else None
        upgrades = self.rng.sample(UPGRADE_REWARDS, 2)
        choices = list(upgrades)
        if protocol is not None:
            choices.append(
                ActionReward(
                    f"protocol:{protocol.plugin_id}",
                    RewardKind.PROTOCOL,
                    protocol.display_name,
                    protocol.description,
                    protocol.plugin_id,
                )
            )
        else:
            choices.append(
                next(reward for reward in UPGRADE_REWARDS if reward not in upgrades)
            )
        self.rng.shuffle(choices)
        return tuple(choices)

    def _protocol_eligible(self, definition: PluginDefinition) -> bool:
        if self.build.get(definition.plugin_id, 0) >= definition.max_stack:
            return False
        owned = {plugin_id for plugin_id, stacks in self.build.items() if stacks > 0}
        reverse_conflict = any(
            definition.plugin_id in self.plugins[plugin_id].conflicts
            for plugin_id in owned
            if plugin_id in self.plugins
        )
        return (
            set(definition.requirements).issubset(owned)
            and not set(definition.conflicts) & owned
            and not reverse_conflict
        )

    def _effects(self) -> tuple[str, ...]:
        return self.state.player_plugin_effects

    def _effect_count(self, effect: str) -> int:
        return self._effects().count(effect)

    def _remove_dead_ai(self) -> None:
        live_ids = set(self.state.entities)
        self.prepared_actions = {
            enemy_id: action
            for enemy_id, action in self.prepared_actions.items()
            if enemy_id in live_ids
        }
        self.enemy_timers = {
            enemy_id: timer
            for enemy_id, timer in self.enemy_timers.items()
            if enemy_id in live_ids
        }

    def _blocked(self, pos: GridPos, ignore_id: str = "") -> bool:
        if not self.state.in_bounds(pos) or pos in self.state.walls:
            return True
        occupant = self.state.entity_at(pos)
        return occupant is not None and occupant.entity_id != ignore_id

    def _in_direction(self, target: GridPos, direction: Direction) -> bool:
        player = self.player
        if player is None:
            return False
        dx = target.x - player.pos.x
        dy = target.y - player.pos.y
        vx, vy = direction.delta
        return (vx != 0 and dy == 0 and dx * vx > 0) or (
            vy != 0 and dx == 0 and dy * vy > 0
        )

    @staticmethod
    def _opposite(direction: Direction) -> Direction:
        return {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT,
        }[direction]

    @staticmethod
    def _direction_toward(origin: GridPos, target: GridPos) -> Direction | None:
        dx = target.x - origin.x
        dy = target.y - origin.y
        if dx and not dy:
            return Direction.RIGHT if dx > 0 else Direction.LEFT
        if dy and not dx:
            return Direction.DOWN if dy > 0 else Direction.UP
        return None

    @staticmethod
    def _enemy_interval(enemy_kind: str) -> float:
        return {
            "melee": 0.96,
            "charger": 1.18,
            "ranged": 1.28,
            "warden": 1.08,
        }.get(enemy_kind, 1.08)
