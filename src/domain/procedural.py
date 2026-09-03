"""Deterministic procedural encounter generation with explicit validation."""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass

from .model import Direction, GridPos


@dataclass(frozen=True)
class ProceduralEnemySpawn:
    entity_id: str
    enemy_kind: str
    pos: GridPos
    hp: int


@dataclass(frozen=True)
class ProceduralEncounter:
    seed: int
    generation_attempt: int
    width: int
    height: int
    floor: frozenset[GridPos]
    walls: frozenset[GridPos]
    hazards: frozenset[GridPos]
    player_spawn: GridPos
    enemies: tuple[ProceduralEnemySpawn, ...]
    reward_pos: GridPos
    room_centers: tuple[GridPos, ...]

    def fingerprint(self) -> tuple[object, ...]:
        return (
            self.seed,
            self.width,
            self.height,
            tuple(sorted(self.floor)),
            tuple(sorted(self.walls)),
            tuple(sorted(self.hazards)),
            self.player_spawn,
            tuple((enemy.enemy_kind, enemy.pos, enemy.hp) for enemy in self.enemies),
            self.reward_pos,
        )


class ProceduralGenerationError(RuntimeError):
    """Raised when every bounded generation attempt fails validation."""


class ProceduralEncounterGenerator:
    def __init__(
        self,
        width: int = 15,
        height: int = 10,
        max_attempts: int = 32,
    ) -> None:
        if width < 11 or height < 8:
            raise ValueError("Procedural maps require at least 11x8 cells")
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        self.width = width
        self.height = height
        self.max_attempts = max_attempts

    def generate(self, seed: int, encounter_index: int = 0) -> ProceduralEncounter:
        for attempt in range(self.max_attempts):
            attempt_seed = seed + encounter_index * 1_000_003 + attempt * 97_409
            encounter = self._generate_attempt(
                random.Random(attempt_seed), seed, encounter_index, attempt
            )
            if validate_encounter(encounter):
                return encounter
        raise ProceduralGenerationError(
            f"seed {seed} failed after {self.max_attempts} attempts"
        )

    def _generate_attempt(
        self,
        rng: random.Random,
        seed: int,
        encounter_index: int,
        attempt: int,
    ) -> ProceduralEncounter:
        floor: set[GridPos] = set()
        centers: list[GridPos] = []
        room_count = rng.randint(4, 6)
        for _ in range(room_count):
            room_width = rng.randint(3, 5)
            room_height = rng.randint(3, 4)
            left = rng.randint(1, self.width - room_width - 1)
            top = rng.randint(1, self.height - room_height - 1)
            cells = {
                GridPos(x, y)
                for x in range(left, left + room_width)
                for y in range(top, top + room_height)
            }
            if floor and len(cells & floor) > len(cells) // 2:
                continue
            floor.update(cells)
            centers.append(GridPos(left + room_width // 2, top + room_height // 2))

        if len(centers) < 3:
            return self._invalid(seed, attempt)

        for first, second in zip(centers, centers[1:]):
            horizontal_first = bool(rng.randrange(2))
            if horizontal_first:
                self._carve_horizontal(floor, first.x, second.x, first.y)
                self._carve_vertical(floor, first.y, second.y, second.x)
            else:
                self._carve_vertical(floor, first.y, second.y, first.x)
                self._carve_horizontal(floor, first.x, second.x, second.y)

        floor = {
            pos for pos in floor
            if 0 < pos.x < self.width - 1 and 0 < pos.y < self.height - 1
        }
        if len(floor) < 34:
            return self._invalid(seed, attempt)

        player = centers[0]
        distances = bfs_distances(player, floor)
        distant = [pos for pos, distance in distances.items() if distance >= 7]
        if len(distant) < 4:
            return self._invalid(seed, attempt)
        distant.sort(key=lambda pos: (-distances[pos], pos.x, pos.y))
        reward = distant[0]

        enemy_count = min(5, 3 + encounter_index)
        enemy_candidates = [pos for pos in distant[1:] if pos != reward]
        rng.shuffle(enemy_candidates)
        selected: list[GridPos] = []
        for candidate in enemy_candidates:
            if all(candidate.manhattan_distance(other) >= 2 for other in selected):
                selected.append(candidate)
            if len(selected) == enemy_count:
                break
        if len(selected) < enemy_count:
            return self._invalid(seed, attempt)

        hazard_candidates = [
            pos for pos in floor
            if distances.get(pos, 0) >= 3
            and pos not in selected
            and pos != reward
            and sum(neighbour in floor for neighbour in _neighbours(pos)) >= 3
        ]
        rng.shuffle(hazard_candidates)
        hazards = frozenset(hazard_candidates[: 2 + encounter_index])
        enemy_kinds = ("melee", "charger", "ranged")
        enemies = tuple(
            ProceduralEnemySpawn(
                f"enemy_{index + 1}",
                "warden" if encounter_index >= 2 and index == 0 else enemy_kinds[index % 3],
                pos,
                12 if encounter_index >= 2 and index == 0 else 3 + encounter_index,
            )
            for index, pos in enumerate(selected)
        )
        all_cells = {
            GridPos(x, y) for x in range(self.width) for y in range(self.height)
        }
        return ProceduralEncounter(
            seed=seed,
            generation_attempt=attempt,
            width=self.width,
            height=self.height,
            floor=frozenset(floor),
            walls=frozenset(all_cells - floor),
            hazards=hazards,
            player_spawn=player,
            enemies=enemies,
            reward_pos=reward,
            room_centers=tuple(centers),
        )

    def _invalid(self, seed: int, attempt: int) -> ProceduralEncounter:
        return ProceduralEncounter(
            seed, attempt, self.width, self.height, frozenset(), frozenset(),
            frozenset(), GridPos(0, 0), (), GridPos(0, 0), ()
        )

    @staticmethod
    def _carve_horizontal(
        floor: set[GridPos], start: int, end: int, y: int
    ) -> None:
        for x in range(min(start, end), max(start, end) + 1):
            floor.add(GridPos(x, y))

    @staticmethod
    def _carve_vertical(
        floor: set[GridPos], start: int, end: int, x: int
    ) -> None:
        for y in range(min(start, end), max(start, end) + 1):
            floor.add(GridPos(x, y))


def bfs_distances(start: GridPos, walkable: frozenset[GridPos] | set[GridPos]) -> dict[GridPos, int]:
    if start not in walkable:
        return {}
    distances = {start: 0}
    queue: deque[GridPos] = deque([start])
    while queue:
        current = queue.popleft()
        for neighbour in _neighbours(current):
            if neighbour in walkable and neighbour not in distances:
                distances[neighbour] = distances[current] + 1
                queue.append(neighbour)
    return distances


def validate_encounter(encounter: ProceduralEncounter) -> bool:
    if not encounter.floor or encounter.player_spawn not in encounter.floor:
        return False
    occupied = {enemy.pos for enemy in encounter.enemies}
    if len(occupied) != len(encounter.enemies):
        return False
    required = occupied | {encounter.reward_pos} | set(encounter.hazards)
    if encounter.player_spawn in required or not required.issubset(encounter.floor):
        return False
    distances = bfs_distances(encounter.player_spawn, encounter.floor)
    if not required.issubset(distances):
        return False
    if any(distances[pos] < 7 for pos in occupied | {encounter.reward_pos}):
        return False
    return not (encounter.hazards & occupied)


def _neighbours(pos: GridPos) -> tuple[GridPos, ...]:
    return tuple(pos.moved(direction) for direction in Direction)
