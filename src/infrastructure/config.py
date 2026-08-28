"""Strict JSON loader for the small Stage03 content surface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.domain.content import (
    EncounterDefinition,
    EnemySpawn,
    LevelDefinition,
    PluginDefinition,
)
from src.domain.model import GridPos

KNOWN_EFFECT_TYPES = {
    "repeat_first_on_empty_third",
    "push_damage_plus_one",
    "pull_range_plus_one",
    "shield_plus_one",
}
KNOWN_ENEMY_KINDS = {"guard", "charger", "sniper"}


class ContentLoadError(ValueError):
    """A readable startup error with file and field context."""


def load_level_one(data_root: Path | None = None) -> tuple[LevelDefinition, dict[str, PluginDefinition]]:
    root = data_root or Path(__file__).resolve().parents[2] / "data"
    plugins_path = root / "plugins" / "protocols.json"
    level_path = root / "levels" / "level_1.json"
    plugins = _load_plugins(plugins_path)
    level = _load_level(level_path, plugins)
    return level, plugins


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContentLoadError(f"Missing content file: {path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContentLoadError(f"Cannot read valid JSON from {path}: {exc}") from exc


def _load_plugins(path: Path) -> dict[str, PluginDefinition]:
    payload = _mapping(_read_json(path), path, "root")
    entries = _list(_required(payload, "plugins", path), path, "plugins")
    plugins: dict[str, PluginDefinition] = {}
    for index, raw in enumerate(entries):
        field = f"plugins[{index}]"
        item = _mapping(raw, path, field)
        plugin_id = _text(_required(item, "id", path, field), path, f"{field}.id")
        if plugin_id in plugins:
            raise ContentLoadError(f"{path}: duplicate plugin id {plugin_id!r}")
        effect_type = _text(_required(item, "effect_type", path, field), path, f"{field}.effect_type")
        if effect_type not in KNOWN_EFFECT_TYPES:
            raise ContentLoadError(f"{path}: {field}.effect_type unknown value {effect_type!r}")
        plugins[plugin_id] = PluginDefinition(
            plugin_id,
            _text(_required(item, "name", path, field), path, f"{field}.name"),
            _text(_required(item, "description", path, field), path, f"{field}.description"),
            effect_type,
        )
    if not plugins:
        raise ContentLoadError(f"{path}: plugins must not be empty")
    return plugins


def _load_level(path: Path, plugins: dict[str, PluginDefinition]) -> LevelDefinition:
    payload = _mapping(_read_json(path), path, "root")
    width = _positive_int(_required(payload, "width", path), path, "width")
    height = _positive_int(_required(payload, "height", path), path, "height")
    encounters_raw = _list(_required(payload, "encounters", path), path, "encounters")
    encounters: list[EncounterDefinition] = []
    encounter_ids: set[str] = set()
    for index, raw in enumerate(encounters_raw):
        field = f"encounters[{index}]"
        item = _mapping(raw, path, field)
        encounter_id = _text(_required(item, "id", path, field), path, f"{field}.id")
        if encounter_id in encounter_ids:
            raise ContentLoadError(f"{path}: duplicate encounter id {encounter_id!r}")
        encounter_ids.add(encounter_id)
        enemies = _load_enemies(item, path, field, width, height)
        walls = frozenset(
            _grid_pos(value, path, f"{field}.walls", width, height)
            for value in _list(item.get("walls", []), path, f"{field}.walls")
        )
        player_spawn = _grid_pos(
            _required(item, "player_spawn", path, field), path, f"{field}.player_spawn", width, height
        )
        occupied = {enemy.pos for enemy in enemies}
        if player_spawn in walls or player_spawn in occupied or walls & occupied:
            raise ContentLoadError(f"{path}: {field} has overlapping player, enemy or wall positions")
        reward_choices = tuple(
            _text(value, path, f"{field}.reward_choices")
            for value in _list(item.get("reward_choices", []), path, f"{field}.reward_choices")
        )
        for plugin_id in reward_choices:
            if plugin_id not in plugins:
                raise ContentLoadError(f"{path}: {field} references unknown plugin {plugin_id!r}")
        climax = item.get("is_climax", False)
        if not isinstance(climax, bool):
            raise ContentLoadError(f"{path}: {field}.is_climax must be a boolean")
        encounters.append(
            EncounterDefinition(
                encounter_id,
                _text(_required(item, "title", path, field), path, f"{field}.title"),
                _text(_required(item, "objective", path, field), path, f"{field}.objective"),
                _text(_required(item, "hint", path, field), path, f"{field}.hint"),
                player_spawn,
                enemies,
                walls,
                reward_choices,
                climax,
            )
        )
    if not encounters:
        raise ContentLoadError(f"{path}: encounters must not be empty")
    return LevelDefinition(
        _text(_required(payload, "id", path), path, "id"),
        _text(_required(payload, "name", path), path, "name"),
        _integer(_required(payload, "seed", path), path, "seed"),
        width,
        height,
        _positive_int(_required(payload, "player_max_hp", path), path, "player_max_hp"),
        tuple(encounters),
    )


def _load_enemies(
    item: dict[str, Any], path: Path, field: str, width: int, height: int
) -> tuple[EnemySpawn, ...]:
    entries = _list(_required(item, "enemies", path, field), path, f"{field}.enemies")
    enemies: list[EnemySpawn] = []
    ids: set[str] = set()
    positions: set[GridPos] = set()
    for index, raw in enumerate(entries):
        enemy_field = f"{field}.enemies[{index}]"
        enemy = _mapping(raw, path, enemy_field)
        entity_id = _text(_required(enemy, "id", path, enemy_field), path, f"{enemy_field}.id")
        if entity_id == "player" or entity_id in ids:
            raise ContentLoadError(f"{path}: duplicate/reserved entity id {entity_id!r}")
        kind = _text(_required(enemy, "kind", path, enemy_field), path, f"{enemy_field}.kind")
        if kind not in KNOWN_ENEMY_KINDS:
            raise ContentLoadError(f"{path}: {enemy_field}.kind unknown value {kind!r}")
        pos = _grid_pos(_required(enemy, "pos", path, enemy_field), path, f"{enemy_field}.pos", width, height)
        if pos in positions:
            raise ContentLoadError(f"{path}: duplicate enemy position {pos}")
        ids.add(entity_id)
        positions.add(pos)
        enemies.append(
            EnemySpawn(
                entity_id,
                _text(_required(enemy, "name", path, enemy_field), path, f"{enemy_field}.name"),
                kind,
                pos,
                _positive_int(_required(enemy, "hp", path, enemy_field), path, f"{enemy_field}.hp"),
            )
        )
    if not enemies:
        raise ContentLoadError(f"{path}: {field}.enemies must not be empty")
    return tuple(enemies)


def _required(data: dict[str, Any], key: str, path: Path, prefix: str = "root") -> Any:
    if key not in data:
        raise ContentLoadError(f"{path}: missing required field {prefix}.{key}")
    return data[key]


def _mapping(value: Any, path: Path, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContentLoadError(f"{path}: {field} must be an object")
    return value


def _list(value: Any, path: Path, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContentLoadError(f"{path}: {field} must be an array")
    return value


def _text(value: Any, path: Path, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContentLoadError(f"{path}: {field} must be non-empty text")
    return value


def _integer(value: Any, path: Path, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContentLoadError(f"{path}: {field} must be an integer")
    return value


def _positive_int(value: Any, path: Path, field: str) -> int:
    result = _integer(value, path, field)
    if result <= 0:
        raise ContentLoadError(f"{path}: {field} must be positive")
    return result


def _grid_pos(value: Any, path: Path, field: str, width: int, height: int) -> GridPos:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(isinstance(part, bool) or not isinstance(part, int) for part in value)
    ):
        raise ContentLoadError(f"{path}: {field} must be [x, y] integers")
    pos = GridPos(value[0], value[1])
    if not (0 <= pos.x < width and 0 <= pos.y < height):
        raise ContentLoadError(f"{path}: {field} position {value} is outside {width}x{height}")
    return pos
