"""Small explainable behavior tree whose prepared action is also enemy intent."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Protocol

from .model import CombatState, Direction, EntityState, GridPos


class BehaviorStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class PreparedActionKind(str, Enum):
    ATTACK = "attack"
    SPECIAL = "special"
    CHASE = "chase"
    RETREAT = "retreat"
    STRAFE = "strafe"
    PATROL = "patrol"


@dataclass(frozen=True)
class PreparedAction:
    actor_id: str
    kind: PreparedActionKind
    target_pos: GridPos
    damage: int = 0
    label: str = ""
    target_positions: tuple[GridPos, ...] = ()


@dataclass
class BehaviorContext:
    state: CombatState
    actor: EntityState
    player: EntityState
    special_ready: bool = False
    prepared_action: PreparedAction | None = None


class BehaviorNode(Protocol):
    def tick(self, context: BehaviorContext) -> BehaviorStatus:
        ...


class Selector:
    def __init__(self, *children: BehaviorNode) -> None:
        self.children = children

    def tick(self, context: BehaviorContext) -> BehaviorStatus:
        for child in self.children:
            if child.tick(context) is BehaviorStatus.SUCCESS:
                return BehaviorStatus.SUCCESS
        return BehaviorStatus.FAILURE


class Sequence:
    def __init__(self, *children: BehaviorNode) -> None:
        self.children = children

    def tick(self, context: BehaviorContext) -> BehaviorStatus:
        for child in self.children:
            if child.tick(context) is BehaviorStatus.FAILURE:
                return BehaviorStatus.FAILURE
        return BehaviorStatus.SUCCESS


class Condition:
    def __init__(self, predicate: Callable[[BehaviorContext], bool]) -> None:
        self.predicate = predicate

    def tick(self, context: BehaviorContext) -> BehaviorStatus:
        return (
            BehaviorStatus.SUCCESS
            if self.predicate(context)
            else BehaviorStatus.FAILURE
        )


class Action:
    def __init__(
        self, prepare: Callable[[BehaviorContext], PreparedAction | None]
    ) -> None:
        self.prepare = prepare

    def tick(self, context: BehaviorContext) -> BehaviorStatus:
        prepared = self.prepare(context)
        if prepared is None:
            return BehaviorStatus.FAILURE
        context.prepared_action = prepared
        return BehaviorStatus.SUCCESS


def build_enemy_tree(enemy_kind: str) -> BehaviorNode:
    attack = Sequence(Condition(_player_in_attack_range), Action(_attack))
    special = Sequence(Condition(_can_use_special), Action(_special))
    visible = Condition(_player_visible)
    if enemy_kind == "charger":
        return Selector(
            attack,
            special,
            Sequence(visible, Condition(_too_close_for_charge), Action(_retreat)),
            Sequence(visible, Action(_chase)),
            Action(_patrol),
        )
    if enemy_kind == "ranged":
        return Selector(
            Sequence(Condition(_ranged_too_close), Action(_retreat)),
            attack,
            Sequence(visible, Condition(_at_ranged_distance), Action(_strafe)),
            Sequence(visible, Action(_chase)),
            Action(_patrol),
        )
    if enemy_kind == "warden":
        return Selector(special, attack, Sequence(visible, Action(_chase)), Action(_patrol))
    return Selector(attack, special, Sequence(visible, Action(_chase)), Action(_patrol))


def plan_enemy_action(
    state: CombatState,
    actor_id: str,
    special_ready: bool = False,
) -> PreparedAction:
    actor = state.entities[actor_id]
    player = state.entities["player"]
    context = BehaviorContext(state, actor, player, special_ready)
    build_enemy_tree(actor.enemy_kind).tick(context)
    return context.prepared_action or PreparedAction(
        actor_id, PreparedActionKind.PATROL, actor.pos, label="REPOSITION"
    )


def _distance(context: BehaviorContext) -> int:
    return context.actor.pos.manhattan_distance(context.player.pos)


def _aligned(context: BehaviorContext) -> bool:
    return (
        context.actor.pos.x == context.player.pos.x
        or context.actor.pos.y == context.player.pos.y
    )


def _player_in_attack_range(context: BehaviorContext) -> bool:
    if context.actor.enemy_kind in {"ranged", "warden"}:
        return _aligned(context) and 2 <= _distance(context) <= 5
    return _distance(context) == 1


def _can_use_special(context: BehaviorContext) -> bool:
    return (
        context.special_ready
        and context.actor.enemy_kind in {"charger", "warden"}
        and _aligned(context)
        and 2 <= _distance(context) <= 5
        and _line_clear(context)
    )


def _player_visible(context: BehaviorContext) -> bool:
    return _distance(context) <= 10


def _too_close_for_charge(context: BehaviorContext) -> bool:
    return _distance(context) < 3


def _ranged_too_close(context: BehaviorContext) -> bool:
    return _distance(context) < 3


def _at_ranged_distance(context: BehaviorContext) -> bool:
    return 3 <= _distance(context) <= 5


def _attack(context: BehaviorContext) -> PreparedAction:
    damage = 3 if context.actor.enemy_kind == "warden" else 2 if context.actor.enemy_kind == "ranged" else 1
    return PreparedAction(
        context.actor.entity_id,
        PreparedActionKind.ATTACK,
        context.player.pos,
        damage,
        "SHOOT" if context.actor.enemy_kind in {"ranged", "warden"} else "STRIKE",
    )


def _special(context: BehaviorContext) -> PreparedAction:
    if context.actor.enemy_kind == "warden":
        targets = [context.player.pos]
        targets.extend(
            target
            for direction in Direction
            if context.state.in_bounds(target := context.player.pos.moved(direction))
            and target not in context.state.walls
        )
        return PreparedAction(
            context.actor.entity_id,
            PreparedActionKind.SPECIAL,
            context.player.pos,
            4,
            "PHASE CROSS",
            tuple(targets),
        )
    return PreparedAction(
        context.actor.entity_id,
        PreparedActionKind.SPECIAL,
        context.player.pos,
        2,
        "CHARGE",
    )


def _chase(context: BehaviorContext) -> PreparedAction | None:
    step = _bfs_step(context, toward=True)
    if step is None:
        return None
    return PreparedAction(context.actor.entity_id, PreparedActionKind.CHASE, step, label="CHASE")


def _retreat(context: BehaviorContext) -> PreparedAction | None:
    step = _best_open_neighbour(context, maximize_distance=True)
    if step is None:
        return None
    return PreparedAction(context.actor.entity_id, PreparedActionKind.RETREAT, step, label="KEEP RANGE")


def _strafe(context: BehaviorContext) -> PreparedAction | None:
    candidates = [
        pos for pos in _open_neighbours(context)
        if 3 <= pos.manhattan_distance(context.player.pos) <= 5
        and not (pos.x == context.player.pos.x or pos.y == context.player.pos.y)
    ]
    if not candidates:
        return _retreat(context)
    target = sorted(
        candidates,
        key=lambda pos: (
            abs(pos.manhattan_distance(context.player.pos) - _distance(context)),
            pos.y,
            pos.x,
        ),
    )[0]
    return PreparedAction(context.actor.entity_id, PreparedActionKind.STRAFE, target, label="STRAFE")


def _patrol(context: BehaviorContext) -> PreparedAction:
    target = _best_open_neighbour(context, maximize_distance=False) or context.actor.pos
    return PreparedAction(context.actor.entity_id, PreparedActionKind.PATROL, target, label="REPOSITION")


def _line_clear(context: BehaviorContext) -> bool:
    actor, player = context.actor.pos, context.player.pos
    if actor.x == player.x:
        cells = (GridPos(actor.x, y) for y in range(min(actor.y, player.y) + 1, max(actor.y, player.y)))
    elif actor.y == player.y:
        cells = (GridPos(x, actor.y) for x in range(min(actor.x, player.x) + 1, max(actor.x, player.x)))
    else:
        return False
    occupied = {
        entity.pos
        for entity in context.state.entities.values()
        if entity.entity_id not in {context.actor.entity_id, context.player.entity_id}
    }
    return all(cell not in context.state.walls and cell not in occupied for cell in cells)


def _open_neighbours(context: BehaviorContext) -> list[GridPos]:
    occupied = {
        entity.pos
        for entity in context.state.entities.values()
        if entity.entity_id != context.actor.entity_id
    }
    return [
        context.actor.pos.moved(direction)
        for direction in Direction
        if context.state.in_bounds(context.actor.pos.moved(direction))
        and context.actor.pos.moved(direction) not in context.state.walls
        and context.actor.pos.moved(direction) not in occupied
    ]


def _best_open_neighbour(
    context: BehaviorContext, maximize_distance: bool
) -> GridPos | None:
    candidates = _open_neighbours(context)
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda pos: (
            -pos.manhattan_distance(context.player.pos)
            if maximize_distance
            else pos.manhattan_distance(context.player.pos),
            pos.y,
            pos.x,
        ),
    )[0]


def _bfs_step(context: BehaviorContext, toward: bool) -> GridPos | None:
    del toward
    start = context.actor.pos
    goal = context.player.pos
    occupied = {
        entity.pos
        for entity in context.state.entities.values()
        if entity.entity_id not in {context.actor.entity_id, context.player.entity_id}
    }
    queue: deque[GridPos] = deque([start])
    parent: dict[GridPos, GridPos | None] = {start: None}
    found: GridPos | None = None
    while queue:
        current = queue.popleft()
        if current.manhattan_distance(goal) == 1:
            found = current
            break
        for direction in Direction:
            nxt = current.moved(direction)
            if (
                nxt in parent
                or not context.state.in_bounds(nxt)
                or nxt in context.state.walls
                or nxt in occupied
                or nxt == goal
            ):
                continue
            parent[nxt] = current
            queue.append(nxt)
    if found is None:
        return None
    while parent[found] not in (None, start):
        found = parent[found]  # type: ignore[assignment]
    return found
