"""Presentation-only timing and event semantics for Stage06 polish."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain import LogicEvent

BASE_EVENT_MS = 190
REDUCED_EVENT_MS = 90
IMPACT_EVENT_MS = 250

IMPACT_KINDS = frozenset({"damaged", "died", "push_blocked"})
MOVEMENT_KINDS = frozenset({"moved", "enemy_moved", "pushed", "pulled"})
SHAKE_KINDS = frozenset({"push_blocked", "died"})

EVENT_CUES = {
    "moved": "move",
    "enemy_moved": "move",
    "pushed": "impact",
    "pulled": "pull",
    "push_blocked": "impact_heavy",
    "shielded": "shield",
    "shield_absorbed": "shield_hit",
    "damaged": "damage",
    "died": "death",
    "plugin_triggered": "protocol",
    "rule_triggered": "inverse",
    "rule_changed": "inverse",
    "rule_held": "anchor",
    "intent_cancelled": "cancel",
}

PLUGIN_LABELS = {
    "echo_protocol": "回声协议 · 重放首拍",
    "resonance_buffer": "共振缓冲 · 回声充能",
    "kinetic_amplifier": "动能增幅 · 推力提升",
    "collision_overload": "碰撞过载 · 墙面增伤",
    "emergency_barrier": "应急屏障 · 护盾增强",
    "aegis_counter": "盾势反推 · 先盾后推",
    "tractor_lock": "牵引锁断 · 意图取消",
    "vector_extender": "矢量延伸 · 牵引增程",
}


@dataclass(frozen=True)
class PresentationFrame:
    event: LogicEvent | None
    event_index: int | None
    progress: float
    shake: tuple[int, int]


def event_duration_ms(event: LogicEvent, reduced_motion: bool) -> int:
    if reduced_motion:
        return REDUCED_EVENT_MS
    return IMPACT_EVENT_MS if event.kind in IMPACT_KINDS else BASE_EVENT_MS


def presentation_frame(
    events: tuple[LogicEvent, ...], elapsed_ms: int, reduced_motion: bool
) -> PresentationFrame:
    visible = tuple(event for event in events if event.kind != "waited")
    if not visible:
        return PresentationFrame(None, None, 1.0, (0, 0))
    remaining = max(0, elapsed_ms)
    for index, event in enumerate(visible):
        duration = event_duration_ms(event, reduced_motion)
        if remaining < duration:
            progress = min(1.0, remaining / max(1, duration))
            shake = _shake(event, remaining, reduced_motion)
            return PresentationFrame(event, index, progress, shake)
        remaining -= duration
    return PresentationFrame(None, None, 1.0, (0, 0))


def cue_for_event(event: LogicEvent) -> str | None:
    if (
        event.kind in {"damaged", "shield_absorbed"}
        and event.detail == "locked_intent"
    ):
        return "enemy_attack"
    return EVENT_CUES.get(event.kind)


def plugin_feedback(event: LogicEvent | None) -> str | None:
    if event is None:
        return None
    if event.kind == "plugin_triggered":
        return PLUGIN_LABELS.get(event.detail, f"协议触发 · {event.detail}")
    if event.kind == "shielded" and event.detail == "resonance_buffer":
        return PLUGIN_LABELS["resonance_buffer"]
    if event.kind == "damaged" and event.detail == "collision":
        return PLUGIN_LABELS["collision_overload"]
    if event.kind == "damaged" and event.detail == "kinetic_amplifier":
        return PLUGIN_LABELS["kinetic_amplifier"]
    return None


def _shake(event: LogicEvent, elapsed_ms: int, reduced_motion: bool) -> tuple[int, int]:
    if reduced_motion or event.kind not in SHAKE_KINDS or elapsed_ms > 120:
        return (0, 0)
    strength = 5 if event.kind == "died" else 3
    phase = elapsed_ms // 22
    return (strength if phase % 2 == 0 else -strength, -strength if phase % 3 == 0 else strength)
