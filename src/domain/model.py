"""确定性战斗模拟所需的结构化值对象。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


@dataclass(frozen=True, order=True)
class GridPos:
    x: int
    y: int

    def moved(self, direction: "Direction") -> "GridPos":
        dx, dy = direction.delta
        return GridPos(self.x + dx, self.y + dy)

    def manhattan_distance(self, other: "GridPos") -> int:
        return abs(self.x - other.x) + abs(self.y - other.y)


class Direction(Enum):
    UP = (0, -1)
    RIGHT = (1, 0)
    DOWN = (0, 1)
    LEFT = (-1, 0)

    @property
    def delta(self) -> tuple[int, int]:
        return self.value


class Faction(str, Enum):
    PLAYER = "player"
    ENEMY = "enemy"


class CommandType(str, Enum):
    WAIT = "wait"
    MOVE = "move"
    PUSH = "push"
    PULL = "pull"
    SHIELD = "shield"


@dataclass
class EntityState:
    entity_id: str
    faction: Faction
    pos: GridPos
    hp: int
    max_hp: int
    display_name: str
    enemy_kind: str = ""
    shield: int = 0

    def clone(self) -> "EntityState":
        return EntityState(
            self.entity_id,
            self.faction,
            self.pos,
            self.hp,
            self.max_hp,
            self.display_name,
            self.enemy_kind,
            self.shield,
        )


@dataclass(frozen=True)
class EnemyIntent:
    actor_id: str
    target_pos: GridPos
    damage: int
    order: int


@dataclass(frozen=True)
class Command:
    actor_id: str
    command_type: CommandType
    slot: int
    direction: Direction | None = None
    target_entity_id: str | None = None

    def in_slot(self, slot: int) -> "Command":
        return Command(
            self.actor_id, self.command_type, slot, self.direction, self.target_entity_id
        )


@dataclass
class CombatState:
    width: int
    height: int
    entities: dict[str, EntityState]
    walls: set[GridPos] = field(default_factory=set)
    enemy_intents: tuple[EnemyIntent, ...] = ()
    turn: int = 1

    def clone(self) -> "CombatState":
        return CombatState(
            self.width,
            self.height,
            {key: entity.clone() for key, entity in self.entities.items()},
            set(self.walls),
            tuple(self.enemy_intents),
            self.turn,
        )

    def in_bounds(self, pos: GridPos) -> bool:
        return 0 <= pos.x < self.width and 0 <= pos.y < self.height

    def entity_at(self, pos: GridPos) -> EntityState | None:
        return next((entity for entity in self.entities.values() if entity.pos == pos), None)


@dataclass(frozen=True)
class LogicEvent:
    kind: str
    tick: int
    actor_id: str
    target_id: str | None = None
    from_pos: GridPos | None = None
    to_pos: GridPos | None = None
    amount: int = 0
    detail: str = ""


@dataclass(frozen=True)
class SimulationResult:
    state: CombatState
    events: tuple[LogicEvent, ...]
