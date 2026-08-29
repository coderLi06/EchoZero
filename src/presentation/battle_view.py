"""Read-only battle data and player-facing labels for the formal renderer."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain import Command, CommandType, CombatState, Direction, LogicEvent, SimulationResult
from src.domain.content import EncounterDefinition, PluginDefinition


@dataclass(frozen=True)
class BattleView:
    state: CombatState
    commands: tuple[Command, ...]
    preview: SimulationResult
    definition: EncounterDefinition
    level_display_name: str
    level_number: int
    progress: tuple[int, int]
    build_summary: tuple[tuple[PluginDefinition, int], ...]
    plugin_definitions: dict[str, PluginDefinition]
    run_seed: int


DIRECTION_LABELS = {
    Direction.UP: "上",
    Direction.RIGHT: "右",
    Direction.DOWN: "下",
    Direction.LEFT: "左",
}

COMMAND_LABELS = {
    CommandType.WAIT: "待机",
    CommandType.MOVE: "移动",
    CommandType.PUSH: "推击",
    CommandType.PULL: "牵引",
    CommandType.SHIELD: "护盾",
}

DETAIL_LABELS = {
    "actor_dead": "执行者已离线",
    "attacker_dead": "攻击源已移除",
    "collision": "墙面碰撞",
    "locked_intent": "锁定攻击",
    "out_of_line": "超出牵引轴线",
    "push": "基础推击",
    "stable": "稳定序列",
    "reverse": "逆相序列",
    "sweep": "多格扫掠",
}

PROTOCOL_CODES = {
    "echo_protocol": "ECHO SEQUENCE",
    "resonance_buffer": "RESONANCE BUFFER",
    "kinetic_amplifier": "KINETIC DRIVE",
    "collision_overload": "COLLISION OVERLOAD",
    "emergency_barrier": "AEGIS BARRIER",
    "aegis_counter": "AEGIS COUNTER",
    "tractor_lock": "TRACTOR LOCK",
    "vector_extender": "VECTOR EXTENDER",
}


def entity_display_name(view: BattleView, entity_id: str | None) -> str:
    if not entity_id:
        return "未知目标"
    entity = view.state.entities.get(entity_id)
    if entity is not None:
        return entity.display_name
    for enemy in view.definition.enemies:
        if enemy.entity_id == entity_id:
            return enemy.display_name
    return "已离线目标"


def command_display_label(command: Command, view: BattleView) -> str:
    label = COMMAND_LABELS[command.command_type]
    if command.direction is not None:
        return f"{label} · {DIRECTION_LABELS[command.direction]}"
    if command.target_entity_id:
        return f"{label} · {entity_display_name(view, command.target_entity_id)}"
    return label


def event_detail_label(event: LogicEvent, view: BattleView) -> str:
    if not event.detail:
        return ""
    plugin = view.plugin_definitions.get(event.detail)
    if plugin is not None:
        return plugin.display_name
    return DETAIL_LABELS.get(event.detail, "")


def protocol_code(plugin_id: str) -> str:
    return PROTOCOL_CODES.get(plugin_id, "TACTICAL PROTOCOL")


def meaningful_rewrite(
    baseline: CombatState | None,
    result: CombatState,
    events: tuple[LogicEvent, ...],
) -> bool:
    """Compare two simulator results using only presentation-level outcome signals."""
    if baseline is None:
        return False
    before_player = baseline.entities.get("player")
    after_player = result.entities.get("player")
    if before_player is None and after_player is not None:
        return True
    if before_player is not None and after_player is not None:
        if after_player.hp > before_player.hp:
            return True
    before_enemies = sum(entity.faction.value == "enemy" for entity in baseline.entities.values())
    after_enemies = sum(entity.faction.value == "enemy" for entity in result.entities.values())
    if after_enemies < before_enemies:
        return True
    return any(event.kind == "intent_cancelled" for event in events)
