"""Presentation-only timing and event semantics for Stage06 polish."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain import CombatState, LogicEvent

BASE_EVENT_MS = 340
REDUCED_EVENT_MS = 90
IMPACT_EVENT_MS = 390
EXECUTE_PREP_MS = 160
REDUCED_PREP_MS = 50
EXECUTE_RESULT_MS = 240
REDUCED_RESULT_MS = 70
CAUSALITY_MS = 820
REDUCED_CAUSALITY_MS = 320
REWARD_ACQUIRE_MS = 680
REDUCED_REWARD_MS = 180

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
    beat_progress: float = 1.0
    active_tick: int | None = None


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
    cursor = 0
    while cursor < len(visible):
        tick = visible[cursor].tick
        end = cursor + 1
        while end < len(visible) and visible[end].tick == tick:
            end += 1
        group = visible[cursor:end]
        duration = max(event_duration_ms(event, reduced_motion) for event in group)
        if remaining < duration:
            segment = duration / len(group)
            local_index = min(len(group) - 1, int(remaining / max(1.0, segment)))
            event = group[local_index]
            event_elapsed = remaining - local_index * segment
            progress = min(1.0, event_elapsed / max(1.0, segment))
            shake = _shake(event, round(event_elapsed), reduced_motion)
            return PresentationFrame(
                event,
                cursor + local_index,
                progress,
                shake,
                min(1.0, remaining / max(1, duration)),
                tick,
            )
        remaining -= duration
        cursor = end
    return PresentationFrame(None, None, 1.0, (0, 0))


def presentation_duration_ms(
    events: tuple[LogicEvent, ...], reduced_motion: bool
) -> int:
    visible = tuple(event for event in events if event.kind != "waited")
    duration = 0
    cursor = 0
    while cursor < len(visible):
        tick = visible[cursor].tick
        end = cursor + 1
        while end < len(visible) and visible[end].tick == tick:
            end += 1
        duration += max(
            event_duration_ms(event, reduced_motion) for event in visible[cursor:end]
        )
        cursor = end
    return duration


def playback_state(
    origin: CombatState,
    events: tuple[LogicEvent, ...],
    frame: PresentationFrame,
) -> CombatState:
    """Replay committed event facts for rendering; never feeds back into combat."""
    state = origin.clone()
    visible = tuple(event for event in events if event.kind != "waited")
    completed = len(visible) if frame.event_index is None else frame.event_index
    if frame.event_index is not None and frame.progress >= 0.55:
        completed += 1
    for event in visible[:completed]:
        if event.kind == "moved":
            entity = state.entities.get(event.actor_id)
            if entity is not None and event.to_pos is not None:
                entity.pos = event.to_pos
        elif event.kind in {"pushed", "pulled"}:
            entity = state.entities.get(event.target_id or "")
            if entity is not None and event.to_pos is not None:
                entity.pos = event.to_pos
        elif event.kind == "shielded":
            entity = state.entities.get(event.actor_id)
            if entity is not None:
                entity.shield += event.amount
        elif event.kind == "shield_absorbed":
            entity = state.entities.get(event.target_id or "")
            if entity is not None:
                entity.shield = max(0, entity.shield - event.amount)
        elif event.kind == "damaged":
            entity = state.entities.get(event.target_id or "")
            if entity is not None:
                entity.hp -= event.amount
        elif event.kind == "died":
            state.entities.pop(event.target_id or "", None)
        elif event.kind == "intent_cancelled":
            state.enemy_intents = tuple(
                intent for intent in state.enemy_intents
                if intent.actor_id != event.actor_id
            )
    return state


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
        return PLUGIN_LABELS.get(event.detail, "协议触发")
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
