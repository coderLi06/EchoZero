"""预演和执行共用的唯一回合模拟器。"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

from .model import Command, CommandType, CombatState, Direction, EntityState, GridPos, LogicEvent, SimulationResult

SLOT_COUNT = 3
PUSH_DAMAGE = 1
COLLISION_DAMAGE = 1
PULL_RANGE = 2


def simulate_turn(state: CombatState, commands: Iterable[Command]) -> SimulationResult:
    """在状态副本上执行一回合，从不修改输入状态。"""
    working = state.clone()
    events: list[LogicEvent] = []
    normalised = _normalise_slots(commands)
    normalised, plugin_events = _apply_protocol_plugins(working, normalised)
    events.extend(plugin_events)
    for tick, command in enumerate(normalised, start=1):
        _apply_command(working, command, tick, events)
    _apply_enemy_intents(working, events)
    working.turn += 1
    return SimulationResult(working, tuple(events))


def preview_turn(state: CombatState, commands: Iterable[Command]) -> SimulationResult:
    return simulate_turn(state, commands)


def execute_turn(state: CombatState, commands: Iterable[Command]) -> SimulationResult:
    return simulate_turn(state, commands)


def state_fingerprint(state: CombatState) -> str:
    payload = {
        "size": [state.width, state.height],
        "turn": state.turn,
        "walls": [[pos.x, pos.y] for pos in sorted(state.walls)],
        "entities": [
            {"id": e.entity_id, "faction": e.faction.value, "pos": [e.pos.x, e.pos.y], "hp": e.hp, "max_hp": e.max_hp, "shield": e.shield, "kind": e.enemy_kind}
            for e in sorted(state.entities.values(), key=lambda item: item.entity_id)
        ],
        "intents": [
            [i.actor_id, i.target_pos.x, i.target_pos.y, i.damage, i.order]
            for i in sorted(state.enemy_intents, key=lambda item: (item.order, item.actor_id))
        ],
        "plugins": list(state.player_plugins),
        "plugin_effects": list(state.player_plugin_effects),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalise_slots(commands: Iterable[Command]) -> tuple[Command, ...]:
    by_slot: dict[int, Command] = {}
    actor_id = "player"
    for command in commands:
        if not 1 <= command.slot <= SLOT_COUNT:
            raise ValueError(f"Command slot must be 1..{SLOT_COUNT}, got {command.slot}")
        if command.slot in by_slot:
            raise ValueError(f"Duplicate command slot: {command.slot}")
        by_slot[command.slot] = command
        actor_id = command.actor_id
    return tuple(by_slot.get(slot, Command(actor_id, CommandType.WAIT, slot)) for slot in range(1, SLOT_COUNT + 1))


def _apply_command(state: CombatState, command: Command, tick: int, events: list[LogicEvent]) -> None:
    actor = state.entities.get(command.actor_id)
    if actor is None:
        events.append(LogicEvent("command_cancelled", tick, command.actor_id, detail="actor_dead"))
        return
    if command.command_type is CommandType.WAIT:
        events.append(LogicEvent("waited", tick, actor.entity_id))
    elif command.command_type is CommandType.MOVE:
        _move(state, actor, command.direction, tick, events)
    elif command.command_type is CommandType.PUSH:
        _push(state, actor, command.direction, tick, events)
    elif command.command_type is CommandType.PULL:
        _pull(state, actor, command.target_entity_id, tick, events)
    elif command.command_type is CommandType.SHIELD:
        amount = 1 + state.player_plugin_effects.count("shield_plus_one")
        actor.shield += amount
        detail = "emergency_barrier" if amount > 1 else ""
        events.append(LogicEvent("shielded", tick, actor.entity_id, amount=amount, detail=detail))


def _move(state: CombatState, actor: EntityState, direction: Direction | None, tick: int, events: list[LogicEvent]) -> None:
    if direction is None:
        raise ValueError("Move command requires a direction")
    destination = actor.pos.moved(direction)
    if _blocked(state, destination):
        events.append(LogicEvent("move_blocked", tick, actor.entity_id, from_pos=actor.pos, to_pos=destination))
        return
    origin = actor.pos
    actor.pos = destination
    events.append(LogicEvent("moved", tick, actor.entity_id, from_pos=origin, to_pos=destination))


def _push(state: CombatState, actor: EntityState, direction: Direction | None, tick: int, events: list[LogicEvent]) -> None:
    if direction is None:
        raise ValueError("Push command requires a direction")
    target = state.entity_at(actor.pos.moved(direction))
    if target is None:
        events.append(LogicEvent("push_missed", tick, actor.entity_id, detail=direction.name.lower()))
        return
    damage = PUSH_DAMAGE + state.player_plugin_effects.count("push_damage_plus_one")
    if (
        "shield_primes_push" in state.player_plugin_effects
        and any(
            event.kind == "shielded"
            and event.actor_id == actor.entity_id
            and event.tick < tick
            for event in events
        )
    ):
        damage += 1
        events.append(LogicEvent("plugin_triggered", tick, actor.entity_id, detail="aegis_counter"))
    detail = "kinetic_amplifier" if damage > PUSH_DAMAGE else "push"
    _damage(state, target, damage, tick, actor.entity_id, events, detail)
    if target.entity_id not in state.entities:
        return
    destination = target.pos.moved(direction)
    if _blocked(state, destination):
        events.append(LogicEvent("push_blocked", tick, actor.entity_id, target.entity_id, target.pos, destination))
        collision_damage = COLLISION_DAMAGE + state.player_plugin_effects.count(
            "collision_damage_plus_one"
        )
        _damage(state, target, collision_damage, tick, actor.entity_id, events, "collision")
        return
    origin = target.pos
    target.pos = destination
    events.append(LogicEvent("pushed", tick, actor.entity_id, target.entity_id, origin, destination))


def _pull(state: CombatState, actor: EntityState, target_entity_id: str | None, tick: int, events: list[LogicEvent]) -> None:
    target = state.entities.get(target_entity_id or "")
    if target is None or target.entity_id == actor.entity_id:
        events.append(LogicEvent("pull_missed", tick, actor.entity_id, target_entity_id))
        return
    dx = actor.pos.x - target.pos.x
    dy = actor.pos.y - target.pos.y
    distance = actor.pos.manhattan_distance(target.pos)
    pull_range = PULL_RANGE + (1 if "pull_range_plus_one" in state.player_plugin_effects else 0)
    if distance > pull_range or (dx != 0 and dy != 0):
        events.append(LogicEvent("pull_missed", tick, actor.entity_id, target.entity_id, detail="out_of_line"))
        return
    direction = _direction_from_delta(dx, dy)
    destination = target.pos.moved(direction)
    if _blocked(state, destination):
        events.append(LogicEvent("pull_blocked", tick, actor.entity_id, target.entity_id, target.pos, destination))
        return
    origin = target.pos
    target.pos = destination
    events.append(LogicEvent("pulled", tick, actor.entity_id, target.entity_id, origin, destination))
    if (
        "pull_cancels_intent" in state.player_plugin_effects
        and any(intent.actor_id == target.entity_id for intent in state.enemy_intents)
    ):
        state.enemy_intents = tuple(
            intent for intent in state.enemy_intents if intent.actor_id != target.entity_id
        )
        events.append(LogicEvent("plugin_triggered", tick, actor.entity_id, target.entity_id, detail="tractor_lock"))
        events.append(LogicEvent("intent_cancelled", tick, target.entity_id, detail="tractor_lock"))


def _apply_enemy_intents(state: CombatState, events: list[LogicEvent]) -> None:
    for intent in sorted(state.enemy_intents, key=lambda item: (item.order, item.actor_id)):
        tick = SLOT_COUNT + intent.order
        if intent.actor_id not in state.entities:
            events.append(LogicEvent("intent_cancelled", tick, intent.actor_id, detail="attacker_dead"))
            continue
        target = state.entity_at(intent.target_pos)
        if target is None:
            events.append(LogicEvent("attack_missed", tick, intent.actor_id, to_pos=intent.target_pos, amount=intent.damage))
            continue
        _damage(state, target, intent.damage, tick, intent.actor_id, events, "locked_intent")


def _damage(state: CombatState, target: EntityState, amount: int, tick: int, actor_id: str, events: list[LogicEvent], detail: str) -> None:
    absorbed = min(target.shield, amount)
    if absorbed:
        target.shield -= absorbed
        amount -= absorbed
        events.append(LogicEvent("shield_absorbed", tick, actor_id, target.entity_id, to_pos=target.pos, amount=absorbed, detail=detail))
    if amount <= 0:
        return
    target.hp -= amount
    events.append(LogicEvent("damaged", tick, actor_id, target.entity_id, to_pos=target.pos, amount=amount, detail=detail))
    if target.hp <= 0:
        del state.entities[target.entity_id]
        events.append(LogicEvent("died", tick, actor_id, target.entity_id, to_pos=target.pos))


def _blocked(state: CombatState, pos: GridPos) -> bool:
    return not state.in_bounds(pos) or pos in state.walls or state.entity_at(pos) is not None


def _direction_from_delta(dx: int, dy: int) -> Direction:
    if dx > 0:
        return Direction.RIGHT
    if dx < 0:
        return Direction.LEFT
    if dy > 0:
        return Direction.DOWN
    if dy < 0:
        return Direction.UP
    raise ValueError("Cannot derive a direction from overlapping positions")


def _apply_protocol_plugins(
    state: CombatState, commands: tuple[Command, ...]
) -> tuple[tuple[Command, ...], tuple[LogicEvent, ...]]:
    """Apply the small, explicit Stage03 protocol registry before simulation.

    The transformation runs inside the shared simulator, so preview and execution
    cannot drift. New effect types still require an implementation and config
    validation instead of arbitrary expressions in JSON.
    """
    transformed = list(commands)
    events: list[LogicEvent] = []
    if (
        "repeat_first_on_empty_third" in state.player_plugin_effects
        and transformed[2].command_type is CommandType.WAIT
        and transformed[0].command_type is not CommandType.WAIT
    ):
        transformed[2] = transformed[0].in_slot(3)
        events.append(
            LogicEvent(
                "plugin_triggered",
                3,
                transformed[0].actor_id,
                detail="echo_protocol",
            )
        )
        if "echo_grants_shield" in state.player_plugin_effects:
            actor = state.entities.get(transformed[0].actor_id)
            if actor is not None:
                actor.shield += 1
                events.append(
                    LogicEvent("shielded", 3, actor.entity_id, amount=1, detail="resonance_buffer")
                )
    return tuple(transformed), tuple(events)
