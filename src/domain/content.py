"""Typed, presentation-free definitions loaded from Stage03 JSON content."""

from __future__ import annotations

from dataclasses import dataclass

from .model import GridPos


@dataclass(frozen=True)
class PluginDefinition:
    plugin_id: str
    display_name: str
    description: str
    effect_type: str
    tags: tuple[str, ...] = ()
    weight: int = 1
    requirements: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    max_stack: int = 1


@dataclass(frozen=True)
class EnemySpawn:
    entity_id: str
    display_name: str
    enemy_kind: str
    pos: GridPos
    hp: int


@dataclass(frozen=True)
class EncounterDefinition:
    encounter_id: str
    title: str
    objective: str
    hint: str
    player_spawn: GridPos
    enemies: tuple[EnemySpawn, ...]
    walls: frozenset[GridPos]
    reward_pool: tuple[str, ...] = ()
    reward_count: int = 3
    is_climax: bool = False


@dataclass(frozen=True)
class LevelDefinition:
    level_id: str
    display_name: str
    seed: int
    width: int
    height: int
    player_max_hp: int
    encounters: tuple[EncounterDefinition, ...]
