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
    for tick, command in enumerate(_normalise_slots(commands), start=1):
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
            {"id": e.entity_id, "faction": e.faction.value, "pos": [e.pos.x, e.pos.y], "hp": e.hp, "max_hp": e.max_hp}
            for e in sorted(state.entities.values(), key=lambda item: item.entity_id)
        ],
        "intents": [
            [i.actor_id, i.target_pos.x, i.target_pos.y, i.damage, i.order]
            for i in sorted(state.enemy_intents, key=lambda item: (item.order, item.actor_id))
        ],
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
    _damage(state, target, PUSH_DAMAGE, tick, actor.entity_id, events, "push")
    if target.entity_id not in state.entities:
        return
    destination = target.pos.moved(direction)
    if _blocked(state, destination):
        events.append(LogicEvent("push_blocked", tick, actor.entity_id, target.entity_id, target.pos, destination))
        _damage(state, target, COLLISION_DAMAGE, tick, actor.entity_id, events, "collision")
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
    if distance > PULL_RANGE or (dx != 0 and dy != 0):
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

