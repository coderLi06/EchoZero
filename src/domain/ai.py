"""可解释的 Stage02 敌人规划：BFS 移动后公开锁定意图。"""

from __future__ import annotations

from collections import deque

from .model import CombatState, Direction, EnemyIntent, Faction, GridPos, LogicEvent


def prepare_enemy_turn(state: CombatState) -> tuple[CombatState, tuple[LogicEvent, ...]]:
    """返回敌人移动并锁定新意图后的状态副本。"""
    working = state.clone()
    working.enemy_intents = ()
    player = next((entity for entity in working.entities.values() if entity.faction is Faction.PLAYER), None)
    if player is None:
        return working, ()

    events: list[LogicEvent] = []
    intents: list[EnemyIntent] = []
    enemies = sorted(
        (entity for entity in working.entities.values() if entity.faction is Faction.ENEMY),
        key=lambda entity: entity.entity_id,
    )
    for order, enemy in enumerate(enemies, start=1):
        goals = _attack_positions(working, player.pos, enemy.enemy_kind)
        step = _bfs_next_step(working, enemy.pos, goals, enemy.entity_id)
        if step is not None and step != enemy.pos:
            origin = enemy.pos
            enemy.pos = step
            events.append(LogicEvent("enemy_moved", 0, enemy.entity_id, from_pos=origin, to_pos=step))

        damage = _attack_damage(enemy.enemy_kind, enemy.pos, player.pos)
        if damage:
            intents.append(EnemyIntent(enemy.entity_id, player.pos, damage, order))
            events.append(LogicEvent("intent_locked", 0, enemy.entity_id, player.entity_id, to_pos=player.pos, amount=damage))

    working.enemy_intents = tuple(intents)
    return working, tuple(events)


def _attack_positions(state: CombatState, player: GridPos, enemy_kind: str) -> set[GridPos]:
    if enemy_kind == "sniper":
        positions = {
            GridPos(x, player.y) for x in range(state.width) if 2 <= abs(x - player.x) <= 4
        } | {
            GridPos(player.x, y) for y in range(state.height) if 2 <= abs(y - player.y) <= 4
        }
    else:
        positions = {player.moved(direction) for direction in Direction}
        if enemy_kind == "charger":
            positions |= {
                GridPos(player.x + direction.delta[0] * 2, player.y + direction.delta[1] * 2)
                for direction in Direction
            }
    return {pos for pos in positions if state.in_bounds(pos) and pos not in state.walls}


def _attack_damage(enemy_kind: str, enemy: GridPos, player: GridPos) -> int:
    distance = enemy.manhattan_distance(player)
    aligned = enemy.x == player.x or enemy.y == player.y
    if enemy_kind == "sniper" and aligned and 2 <= distance <= 4:
        return 2
    if enemy_kind == "charger" and aligned and 1 <= distance <= 2:
        return 1
    return 1 if distance == 1 else 0


def _bfs_next_step(state: CombatState, start: GridPos, goals: set[GridPos], actor_id: str) -> GridPos | None:
    """在无权网格上寻找任一攻击位；复杂度 O(width * height)。"""
    if start in goals:
        return start
    occupied = {entity.pos for entity in state.entities.values() if entity.entity_id != actor_id}
    queue: deque[GridPos] = deque([start])
    parent: dict[GridPos, GridPos | None] = {start: None}
    found: GridPos | None = None
    while queue:
        current = queue.popleft()
        if current in goals:
            found = current
            break
        for direction in Direction:
            nxt = current.moved(direction)
            if nxt in parent or not state.in_bounds(nxt) or nxt in state.walls or nxt in occupied:
                continue
            parent[nxt] = current
            queue.append(nxt)
    if found is None:
        return None
    while parent[found] not in (None, start):
        found = parent[found]  # type: ignore[assignment]
    return found
