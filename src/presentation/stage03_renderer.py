"""Formal Stage03 pygame renderer. It only reads domain state and logic events."""

from __future__ import annotations

from typing import Any

import pygame

from src.domain import Command, CommandType, Faction, GridPos, LevelPhase, LogicEvent, TimelineRule
from src.presentation.battle_view import (
    command_display_label,
    entity_display_name,
    event_detail_label,
    protocol_code,
)
from src.presentation.effects import MOVEMENT_KINDS, plugin_feedback

WINDOW_SIZE = (1280, 800)
SAFE_TOP = 28
SAFE_SIDE = 48
CELL_SIZE = 72
GRID_ORIGIN = (48, 174)
PANEL_X = 664
SLOT_RECTS = tuple(pygame.Rect(PANEL_X, 306 + index * 78, 568, 64) for index in range(3))
INTENT_RECT = pygame.Rect(PANEL_X, 146, 568, 92)
TIMELINE_RECT = pygame.Rect(PANEL_X, 246, 568, 48)
EXECUTE_RECT = pygame.Rect(PANEL_X, 558, 370, 58)
RESTART_RECT = pygame.Rect(1050, 558, 182, 58)
PREVIEW_RECT = pygame.Rect(PANEL_X, 626, 568, 38)
CORE_RECT = pygame.Rect(PANEL_X, 96, 246, 42)
PROTOCOL_RECT = pygame.Rect(PANEL_X + 258, 96, 310, 42)
MENU_START_RECT = pygame.Rect(460, 568, 360, 64)
REWARD_RECTS = tuple(pygame.Rect(96 + index * 376, 260, 336, 300) for index in range(3))
RESULT_RESTART_RECT = pygame.Rect(448, 586, 384, 62)
TUTORIAL_NEXT_RECT = pygame.Rect(326, 694, 138, 48)
TUTORIAL_SKIP_RECT = pygame.Rect(474, 694, 138, 48)

COLORS = {
    "background": (7, 10, 18),
    "surface": (19, 27, 42),
    "surface_high": (28, 40, 60),
    "border": (57, 78, 106),
    "text": (241, 247, 255),
    "muted": (166, 183, 207),
    "primary": (58, 210, 255),
    "primary_dark": (12, 78, 103),
    "violet": (169, 119, 255),
    "danger": (255, 91, 123),
    "danger_dark": (78, 24, 41),
    "success": (86, 232, 170),
    "warning": (255, 205, 92),
    "grid_a": (13, 23, 36),
    "grid_b": (17, 30, 46),
    "wall": (67, 83, 107),
    "cyan_glow": (103, 232, 255),
    "violet_dark": (49, 28, 79),
}

EVENT_LABELS = {
    "enemy_moved": "威胁重新定位",
    "intent_locked": "意图已锁定",
    "moved": "位移完成",
    "pushed": "推击位移",
    "pulled": "牵引位移",
    "damaged": "伤害结算",
    "died": "目标离线",
    "shielded": "护盾建立",
    "shield_absorbed": "护盾吸收",
    "attack_missed": "锁定落空",
    "intent_cancelled": "意图取消",
    "push_missed": "推击落空",
    "pull_missed": "牵引失败",
    "move_blocked": "路径阻断",
    "push_blocked": "碰撞发生",
    "plugin_triggered": "协议触发",
    "rule_triggered": "逆相改写",
    "rule_changed": "规则切换",
    "rule_held": "相位锁定",
    "command_cancelled": "命令取消",
    "pull_blocked": "牵引受阻",
}

ENEMY_LABELS = {
    "charger": "突进",
    "sniper": "锁定",
    "sweeper": "扫掠",
    "warden": "相位守卫",
}


class Stage03Renderer:
    def __init__(self, screen: pygame.Surface) -> None:
        self.output = screen
        self.screen = pygame.Surface(WINDOW_SIZE)
        self.fonts: dict[tuple[int, bool, str], pygame.font.Font] = {}
        self.text_cache: dict[tuple[str, int, tuple[int, int, int], bool, str], pygame.Surface] = {}
        self.viewport = pygame.Rect((0, 0), WINDOW_SIZE)

    def draw(self, app: Any) -> None:
        self._background(app)
        scene = app.scene.value
        if scene == "menu":
            self._menu()
        elif scene == "battle":
            self._battle(app)
        elif scene == "reward":
            self._reward(app)
        elif scene == "transition":
            self._transition(app)
        elif scene == "result":
            self._result(app)
        else:
            self._error(app.load_error or "未知资源错误")
        self._global_status(app)
        shake = app.presentation.shake if scene == "battle" else (0, 0)
        self.output.fill(COLORS["background"])
        composed = pygame.Surface(WINDOW_SIZE)
        composed.fill(COLORS["background"])
        composed.blit(self.screen, shake)
        output_size = self.output.get_size()
        scale = min(output_size[0] / WINDOW_SIZE[0], output_size[1] / WINDOW_SIZE[1])
        scaled_size = (
            max(1, round(WINDOW_SIZE[0] * scale)),
            max(1, round(WINDOW_SIZE[1] * scale)),
        )
        self.viewport = pygame.Rect(
            (output_size[0] - scaled_size[0]) // 2,
            (output_size[1] - scaled_size[1]) // 2,
            *scaled_size,
        )
        scaled = (
            composed
            if scaled_size == WINDOW_SIZE
            else pygame.transform.smoothscale(composed, scaled_size)
        )
        self.output.blit(scaled, self.viewport)

    def to_logical(self, pos: tuple[int, int]) -> tuple[int, int] | None:
        if not self.viewport.collidepoint(pos):
            return None
        x = round((pos[0] - self.viewport.x) * WINDOW_SIZE[0] / self.viewport.width)
        y = round((pos[1] - self.viewport.y) * WINDOW_SIZE[1] / self.viewport.height)
        return (min(WINDOW_SIZE[0] - 1, x), min(WINDOW_SIZE[1] - 1, y))

    def _background(self, app: Any) -> None:
        reactor = getattr(app, "level_index", 0) == 1
        self.screen.fill((14, 6, 24) if reactor else COLORS["background"])
        line_color = (38, 17, 55) if reactor else (11, 20, 32)
        for x in range(0, WINDOW_SIZE[0], 64):
            pygame.draw.line(self.screen, line_color, (x, 0), (x, WINDOW_SIZE[1]))
        for y in range(0, WINDOW_SIZE[1], 64):
            pygame.draw.line(self.screen, line_color, (0, y), (WINDOW_SIZE[0], y))
        accent = COLORS["violet"] if reactor else COLORS["primary"]
        pygame.draw.line(self.screen, accent, (0, 0), (WINDOW_SIZE[0], 0), 3)

    def _menu(self) -> None:
        self._center("TACTICAL CAUSALITY // DUAL-SECTOR RUN", 13, COLORS["muted"], (640, 72), True, "data")
        for radius, alpha_color in ((116, COLORS["primary_dark"]), (96, COLORS["violet_dark"])):
            self._diamond((640, 222), radius, alpha_color, 2)
        self._diamond((640, 222), 82, COLORS["primary"], 4)
        self._diamond((640, 222), 52, COLORS["violet"], 2)
        pygame.draw.circle(self.screen, COLORS["text"], (640, 222), 10)
        self._center("ECHO // ZERO", 54, COLORS["text"], (640, 344), True)
        self._center("CALIBRATION // INVERSE REACTOR", 18, COLORS["primary"], (640, 398), True)
        self._center("编排三拍 · 看见因果 · 改写结果", 22, COLORS["muted"], (640, 452))
        self._button(MENU_START_RECT, "开始校准  [ENTER]", True)
        self._center("双区域  /  六场遭遇  /  协议继承  /  逆相终局", 15, COLORS["muted"], (640, 674))

    def _battle(self, app: Any) -> None:
        view = app.battle_view
        definition = view.definition
        current, total = view.progress
        level_color = COLORS["violet"] if view.level_number == 2 else COLORS["primary"]
        self._text_at("ECHO // ZERO", 14, COLORS["muted"], (SAFE_SIDE, SAFE_TOP), True, "display")
        self._text_at(
            f"LEVEL {view.level_number:02}  {view.level_display_name}",
            15,
            level_color,
            (SAFE_SIDE, SAFE_TOP + 26),
            True,
            "data",
        )
        self._progress(app, current, total)
        self._text_at(definition.title, 27, COLORS["text"], (SAFE_SIDE, 90), True, "display")
        self._text_at(definition.objective, 15, COLORS["muted"], (SAFE_SIDE, 128))
        self._draw_board(app)
        self._draw_hud(app)
        self._draw_event_strip(app)
        self._rule_overlay(app)
        self._execution_overlay(app)
        self._tutorial_highlight(app)

    def _progress(self, app: Any, current: int, total: int) -> None:
        start_x = 950
        for index in range(total):
            center = (start_x + index * 92, 48)
            color = COLORS["primary"] if index < current else COLORS["border"]
            if index:
                pygame.draw.line(self.screen, COLORS["border"], (center[0] - 76, 48), (center[0] - 16, 48), 2)
            pygame.draw.circle(self.screen, color, center, 11, 3)
            if index < current - 1:
                pygame.draw.circle(self.screen, color, center, 5)
            if index == current - 1 and not app.ui.reduced_motion:
                pulse = 13 + (pygame.time.get_ticks() // 100) % 4
                pygame.draw.circle(self.screen, color, center, pulse, 1)
            self._center(str(index + 1), 12, COLORS["text"], (center[0], 76), True)

    def _draw_board(self, app: Any) -> None:
        view = app.battle_view
        state = app.visual_state
        frame = app.presentation
        active = frame.event
        player = state.entities.get("player")
        anchored = player is not None and player.pos in state.rule_nodes
        for y in range(state.height):
            for x in range(state.width):
                pos = GridPos(x, y)
                rect = self.cell_rect(pos)
                pygame.draw.rect(self.screen, COLORS["grid_a"] if (x + y) % 2 == 0 else COLORS["grid_b"], rect)
                pygame.draw.rect(self.screen, COLORS["border"], rect, 1)
                if (x * 7 + y * 3) % 5 == 0:
                    pygame.draw.line(self.screen, (23, 48, 65), rect.topleft, (rect.x + 15, rect.y), 2)
        for wall in state.walls:
            rect = self.cell_rect(wall).inflate(-12, -12)
            pygame.draw.polygon(self.screen, COLORS["wall"], [(rect.left, rect.centery), (rect.centerx, rect.top), (rect.right, rect.centery), (rect.centerx, rect.bottom)])
            pygame.draw.line(self.screen, COLORS["muted"], (rect.left + 8, rect.centery), (rect.right - 8, rect.centery), 2)
        for node in state.rule_nodes:
            rect = self.cell_rect(node).inflate(-10, -10)
            is_active = player is not None and player.pos == node
            pulse = 3 if app.ui.reduced_motion else (pygame.time.get_ticks() // 90) % 5
            pygame.draw.rect(self.screen, (18, 70, 62), rect, border_radius=12)
            pygame.draw.rect(self.screen, COLORS["text"] if is_active else COLORS["success"], rect, 4 if is_active else 2, border_radius=12)
            pygame.draw.circle(self.screen, COLORS["success"], rect.center, 19 + pulse, 2)
            self._center("锁相" if is_active else "锚", 12, COLORS["text"], rect.center, True)
        for intent in state.enemy_intents:
            target = self.cell_rect(intent.target_pos).inflate(-6, -6)
            hot = bool(app.execution_active and (frame.active_tick or 0) > 3)
            pygame.draw.rect(self.screen, (48, 19, 34), target, border_radius=10)
            pygame.draw.rect(self.screen, COLORS["danger"], target, 3 if hot else 1, border_radius=10)
            for offset in range(-target.height, target.width, 14):
                pygame.draw.line(self.screen, (151, 45, 72) if hot else (92, 35, 55), (target.x + offset, target.bottom), (target.x + offset + target.height, target.top), 1)
            actor = state.entities.get(intent.actor_id)
            if actor is not None:
                pygame.draw.line(self.screen, COLORS["danger"], self.cell_rect(actor.pos).center, target.center, 3 if hot else 1)
            self._center(f"! {intent.order}", 15, COLORS["text"], target.center, True)
        if not app.execution_active:
            self._preview_ghosts(view, state)
        moving_id = self._moving_entity_id(active)
        for entity in state.entities.values():
            if entity.entity_id == moving_id and active is not None and active.from_pos and active.to_pos:
                eased = 1 - (1 - frame.progress) ** 3
                origin = self.cell_rect(active.from_pos).center
                destination = self.cell_rect(active.to_pos).center
                center = (
                    round(origin[0] + (destination[0] - origin[0]) * eased),
                    round(origin[1] + (destination[1] - origin[1]) * eased),
                )
                self._entity(entity, center, False)
            else:
                flash = active is not None and active.kind == "damaged" and active.target_id == entity.entity_id and frame.progress < 0.55
                pulse = 0
                if entity.faction is Faction.PLAYER and not app.ui.reduced_motion:
                    pulse = (pygame.time.get_ticks() // 180) % 2
                    if active is not None and 1 <= active.tick <= 3:
                        pulse += 2
                self._entity(entity, flash=flash, pulse=pulse)
        if active is not None:
            self._event_vector(active, state, frame.progress)
            effect_pos = active.to_pos
            actor = state.entities.get(active.actor_id)
            if effect_pos is None and active.kind == "shielded" and actor is not None:
                effect_pos = actor.pos
            if effect_pos is not None:
                self._event_effect(active, effect_pos, frame.progress)
        if anchored:
            self._text_at("PHASE LOCKED // 规则保持", 13, COLORS["success"], (48, 590), True)

    def _preview_ghosts(self, view: Any, state: Any) -> None:
        overlay = pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)
        for event in view.preview.events:
            if event.tick > 3 or event.to_pos is None or event.from_pos is None:
                continue
            if event.kind not in {"moved", "pulled", "pushed"}:
                continue
            source = self.cell_rect(event.from_pos).center
            target = self.cell_rect(event.to_pos).center
            color = (*COLORS["primary"], 92) if event.kind == "moved" else (*COLORS["danger"], 78)
            pygame.draw.line(overlay, color, source, target, 2)
            self._arrow_head(overlay, source, target, color)
        for entity_id, predicted in view.preview.state.entities.items():
            current = state.entities.get(entity_id)
            if current is None or current.pos == predicted.pos:
                continue
            center = self.cell_rect(predicted.pos).center
            color = COLORS["primary"] if predicted.faction is Faction.PLAYER else COLORS["danger"]
            rgba = (*color, 92)
            if predicted.faction is Faction.PLAYER:
                points = [(center[0], center[1] - 23), (center[0] + 23, center[1]), (center[0], center[1] + 23), (center[0] - 23, center[1])]
                pygame.draw.polygon(overlay, rgba, points, 3)
            else:
                pygame.draw.circle(overlay, rgba, center, 23, 3)
            pygame.draw.circle(overlay, (*COLORS["text"], 108), center, 4)
        self.screen.blit(overlay, (0, 0))

    @staticmethod
    def _arrow_head(surface: pygame.Surface, source: tuple[int, int], target: tuple[int, int], color: Any) -> None:
        dx = target[0] - source[0]
        dy = target[1] - source[1]
        length = max(1.0, (dx * dx + dy * dy) ** 0.5)
        ux, uy = dx / length, dy / length
        left = (round(target[0] - ux * 10 - uy * 5), round(target[1] - uy * 10 + ux * 5))
        right = (round(target[0] - ux * 10 + uy * 5), round(target[1] - uy * 10 - ux * 5))
        pygame.draw.polygon(surface, color, (target, left, right))

    def _event_vector(self, event: LogicEvent, state: Any, progress: float) -> None:
        fade = max(0.15, 1.0 - progress)
        if event.from_pos is not None and event.to_pos is not None and event.kind in MOVEMENT_KINDS:
            source = self.cell_rect(event.from_pos).center
            target = self.cell_rect(event.to_pos).center
            color = COLORS["danger"] if event.kind == "enemy_moved" else COLORS["primary"]
            width = max(1, round(5 * fade))
            pygame.draw.line(self.screen, color, source, target, width)
            self._arrow_head(self.screen, source, target, color)
        if event.kind in {"attack_missed", "damaged", "shield_absorbed"} and event.to_pos is not None:
            actor = state.entities.get(event.actor_id)
            if actor is not None:
                source = self.cell_rect(actor.pos).center
                target = self.cell_rect(event.to_pos).center
                pygame.draw.line(self.screen, COLORS["danger"], source, target, max(1, round(4 * fade)))
            if event.kind == "attack_missed":
                self._center("MISS / 攻击落空", 13, COLORS["danger"], (self.cell_rect(event.to_pos).centerx, self.cell_rect(event.to_pos).y - 8), True, "data")
        if event.kind in {"push_missed", "pull_missed"}:
            actor = state.entities.get(event.actor_id)
            if actor is not None:
                self._center("MISS / 落空", 13, COLORS["primary"], (self.cell_rect(actor.pos).centerx, self.cell_rect(actor.pos).y - 8), True, "data")

    def _entity(self, entity: Any, center: tuple[int, int] | None = None, flash: bool = False, pulse: int = 0) -> None:
        rect = self.cell_rect(entity.pos).inflate(-14, -14)
        center = center or rect.center
        color_override = COLORS["text"] if flash else None
        if entity.faction is Faction.PLAYER:
            if pulse:
                self._diamond(center, 29 + pulse, COLORS["primary_dark"], 2)
            self._diamond(center, 26, color_override or COLORS["primary"], 0)
            self._diamond(center, 17, COLORS["background"], 0)
            pygame.draw.circle(self.screen, COLORS["text"], center, 6)
        elif entity.enemy_kind == "charger":
            pygame.draw.polygon(self.screen, color_override or COLORS["danger"], [(center[0] + 25, center[1]), (center[0] - 22, center[1] - 23), (center[0] - 22, center[1] + 23)])
            pygame.draw.polygon(self.screen, COLORS["background"], [(center[0] + 8, center[1]), (center[0] - 10, center[1] - 9), (center[0] - 10, center[1] + 9)])
        elif entity.enemy_kind == "sniper":
            pygame.draw.circle(self.screen, COLORS["violet"], center, 25, 4)
            pygame.draw.circle(self.screen, COLORS["danger"], center, 8)
            pygame.draw.line(self.screen, COLORS["violet"], (center[0] - 30, center[1]), (center[0] + 30, center[1]), 2)
            pygame.draw.line(self.screen, COLORS["violet"], (center[0], center[1] - 30), (center[0], center[1] + 30), 2)
        elif entity.enemy_kind in {"sweeper", "warden"}:
            color = COLORS["danger"]
            self._diamond(center, 27, color, 4)
            pygame.draw.line(self.screen, color, (center[0] - 29, center[1]), (center[0] + 29, center[1]), 4)
            pygame.draw.circle(self.screen, COLORS["danger"], center, 7)
        else:
            points = [(center[0] + 25, center[1]), (center[0] + 12, center[1] + 22), (center[0] - 12, center[1] + 22), (center[0] - 25, center[1]), (center[0] - 12, center[1] - 22), (center[0] + 12, center[1] - 22)]
            pygame.draw.polygon(self.screen, COLORS["danger"], points, 4)
        bar = pygame.Rect(center[0] - rect.width // 2, center[1] + rect.height // 2 + 5, rect.width, 5)
        pygame.draw.rect(self.screen, COLORS["danger_dark"], bar)
        fill = bar.copy()
        fill.width = max(0, round(bar.width * entity.hp / entity.max_hp))
        pygame.draw.rect(self.screen, COLORS["success"] if entity.faction is Faction.PLAYER else COLORS["danger"], fill)

    @staticmethod
    def _moving_entity_id(event: LogicEvent | None) -> str | None:
        if event is None or event.kind not in MOVEMENT_KINDS:
            return None
        return event.target_id if event.kind in {"pushed", "pulled"} else event.actor_id

    def _event_effect(self, event: LogicEvent, pos: GridPos, progress: float) -> None:
        center = self.cell_rect(pos).center
        fade = max(0.0, 1.0 - progress)
        radius = round(14 + progress * 30)
        color = COLORS["danger"] if event.kind in {"damaged", "died", "push_blocked"} else COLORS["primary"]
        if event.kind in {"shielded", "shield_absorbed"}:
            color = COLORS["primary"]
            pygame.draw.circle(self.screen, color, center, radius, max(1, round(5 * fade)))
        elif event.kind == "died":
            for direction in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)):
                end = (center[0] + round(direction[0] * radius), center[1] + round(direction[1] * radius))
                pygame.draw.line(self.screen, color, center, end, max(1, round(4 * fade)))
            self._center("BREAK", 13, COLORS["text"], center, True)
        else:
            pygame.draw.rect(self.screen, color, self.cell_rect(pos).inflate(-radius // 2, -radius // 2), max(1, round(4 * fade)), border_radius=10)
        if event.kind in {"damaged", "shield_absorbed"} and event.amount:
            sign = "-" if event.kind == "damaged" else "BLOCK "
            self._center(f"{sign}{event.amount}", 18, color, (center[0], center[1] - 32 - round(progress * 16)), True)

    def _draw_hud(self, app: Any) -> None:
        view = app.battle_view
        state = app.visual_state
        player = state.entities.get("player")
        hp = "--" if player is None else f"{player.hp}/{player.max_hp}"
        shield = "--" if player is None else str(player.shield)
        active = app.presentation.event
        core_color = COLORS["text"]
        if active is not None and active.target_id == "player":
            core_color = COLORS["primary"] if active.kind == "shield_absorbed" else COLORS["danger"]
        elif active is not None and active.actor_id == "player" and active.kind == "shielded":
            core_color = COLORS["primary"]
        self._panel(CORE_RECT, core_color if core_color != COLORS["text"] else COLORS["border"])
        self._text_at(
            f"CORE {hp}  //  SHIELD {shield}",
            14,
            core_color,
            (CORE_RECT.x + 12, CORE_RECT.y + 11),
            True,
            "data",
        )
        self._protocol_hud(app, view)
        intent_rect = INTENT_RECT
        self._panel(intent_rect, COLORS["danger"] if state.enemy_intents else COLORS["border"])
        self._text_at("ENEMY INTENT / 公开意图", 14, COLORS["danger"], (intent_rect.x + 16, intent_rect.y + 12), True, "data")
        intents = state.enemy_intents
        if not intents:
            self._text_at("SAFE  当前没有可执行的锁定攻击", 14, COLORS["success"], (intent_rect.x + 16, intent_rect.y + 46), True)
        else:
            by_actor: dict[str, list[Any]] = {}
            for item in intents:
                by_actor.setdefault(item.actor_id, []).append(item)
            lines = []
            for actor_id, items in by_actor.items():
                actor = state.entities.get(actor_id)
                kind = ENEMY_LABELS.get(getattr(actor, "enemy_kind", ""), "攻击")
                cells = " / ".join(f"({item.target_pos.x},{item.target_pos.y})" for item in items)
                lines.append(f"{kind}  目标 {cells}  ·  伤害 {items[0].damage}  ·  敌方阶段")
            for index, line in enumerate(lines[:2]):
                self._text_at(line, 13, COLORS["text"], (intent_rect.x + 16, intent_rect.y + 40 + index * 23), True)
        final_rule = (
            view.preview.state.active_timeline_rule
            if app.execution_active
            else state.active_timeline_rule
        )
        rule = self._display_rule(app, final_rule)
        self._timeline_bar(app, rule)
        for index, command in enumerate(view.commands):
            rect = self._slot_visual_rect(app, index)
            selected = app.ui.selected_slot == index
            execution_tick = 3 - index if rule is TimelineRule.REVERSE else index + 1
            active_tick = app.presentation.active_tick or -1
            is_executing = active_tick == execution_tick
            hovered = app.ui.hovered_slot == index and not app.execution_active
            action_color = COLORS["violet"] if rule is TimelineRule.REVERSE else COLORS["primary"]
            border = action_color if is_executing or selected else COLORS["primary_dark"] if hovered else COLORS["border"]
            self._panel(rect, border, selected or is_executing or hovered)
            badge = pygame.Rect(rect.x + 10, rect.y + 10, 44, 44)
            pygame.draw.rect(self.screen, COLORS["violet_dark"] if rule is TimelineRule.REVERSE else COLORS["primary_dark"], badge, border_radius=8)
            self._center(str(index + 1), 18, action_color, badge.center, True, "data")
            self._text_at(command_display_label(command, view), 17, COLORS["text"], (rect.x + 70, rect.y + 8), True)
            self._text_at(f"执行第 {execution_tick} 拍  ·  {app.preview_label(execution_tick)}", 13, COLORS["muted"], (rect.x + 70, rect.y + 36))
            if app.execution_active and not is_executing:
                shade = pygame.Surface(rect.size, pygame.SRCALPHA)
                shade.fill((7, 10, 18, 105))
                self.screen.blit(shade, rect)
        self._button(EXECUTE_RECT, "执行中 // 因果链路" if app.execution_active else "确认执行  [ENTER]", True)
        self._button(RESTART_RECT, "重新校准  [R]", False)
        preview = view.preview.state
        preview_player = preview.entities.get("player")
        enemy_count = sum(entity.faction is Faction.ENEMY for entity in preview.entities.values())
        preview_hp = preview_player.hp if preview_player else 0
        preview_shield = preview_player.shield if preview_player else 0
        prediction = (
            f"预演终态  CORE {preview_hp}  /  SHIELD {preview_shield}"
            f"  /  威胁 {enemy_count}"
        )
        self._text_at(prediction, 15, COLORS["success"] if preview_player else COLORS["danger"], (PANEL_X, 638), True)
        self._text_at(view.definition.hint, 14, COLORS["primary"], (PANEL_X, 670))
        self._text_at(app.ui.feedback, 13, COLORS["muted"], (PANEL_X, 702))
        banner = plugin_feedback(app.presentation.event)
        if banner:
            rect = pygame.Rect(120, 116, 408, 46)
            self._panel(rect, COLORS["violet"], True)
            self._center(f"◆  BUILD ONLINE  //  {banner}", 14, COLORS["text"], rect.center, True)

    def _protocol_hud(self, app: Any, view: Any) -> None:
        self._panel(PROTOCOL_RECT, COLORS["violet"] if view.build_summary else COLORS["border"])
        self._text_at("PROTOCOL", 10, COLORS["violet"], (PROTOCOL_RECT.x + 58, PROTOCOL_RECT.y + 5), True, "data")
        if not view.build_summary:
            self._text_at("未安装", 14, COLORS["muted"], (PROTOCOL_RECT.x + 12, PROTOCOL_RECT.y + 19), True)
            return
        core, stacks = view.build_summary[0]
        self._protocol_icon(core.plugin_id, (PROTOCOL_RECT.x + 34, PROTOCOL_RECT.centery + 4), 15)
        name = core.display_name + (f" ×{stacks}" if stacks > 1 else "")
        self._text_at(name, 14, COLORS["text"], (PROTOCOL_RECT.x + 58, PROTOCOL_RECT.y + 17), True)
        self._text_at(protocol_code(core.plugin_id), 9, COLORS["violet"], (PROTOCOL_RECT.x + 170, PROTOCOL_RECT.y + 6), True, "data")
        for index, (plugin, _) in enumerate(view.build_summary[1:4]):
            self._protocol_icon(plugin.plugin_id, (PROTOCOL_RECT.right - 18 - index * 28, PROTOCOL_RECT.centery + 5), 10)
        if app.ui.protocol_hovered:
            tooltip = pygame.Rect(PANEL_X, 716, 568, 38)
            self._panel(tooltip, COLORS["violet"], True)
            self._text_at(core.description, 12, COLORS["text"], (tooltip.x + 12, tooltip.y + 11))

    @staticmethod
    def _slot_visual_rect(app: Any, index: int) -> pygame.Rect:
        target = SLOT_RECTS[index]
        pair = app.ui.swap_pair
        if pair is None or app.ui.reduced_motion:
            return target
        elapsed = pygame.time.get_ticks() - app.ui.swap_started_ms
        progress = min(1.0, elapsed / 160)
        if progress >= 1.0:
            return target
        if index not in pair:
            return target
        other = pair[1] if index == pair[0] else pair[0]
        origin = SLOT_RECTS[other]
        eased = 1 - (1 - progress) ** 3
        return pygame.Rect(
            round(origin.x + (target.x - origin.x) * eased),
            round(origin.y + (target.y - origin.y) * eased),
            target.width,
            target.height,
        )

    def _timeline_bar(self, app: Any, rule: TimelineRule) -> None:
        rect = TIMELINE_RECT
        inverse = rule is TimelineRule.REVERSE
        color = COLORS["violet"] if inverse else COLORS["primary"]
        self._panel(rect, color, inverse)
        phase_label = {
            "prepare": "PREPARE / 准备",
            "result": "RESULT / 结算",
            "rewrite": "CAUSALITY / 改写",
        }.get(app.execution_phase, "逆相执行" if inverse else "稳定执行")
        self._text_at(phase_label, 14, color, (rect.x + 14, rect.y + 14), True, "data")
        order = (3, 2, 1) if inverse else (1, 2, 3)
        active_tick = app.presentation.active_tick or -1
        flip_event = app.presentation.event
        flipping = (
            flip_event is not None
            and flip_event.kind == "rule_changed"
            and not app.ui.reduced_motion
        )
        old_order = tuple(reversed(order))
        for execution_index, slot in enumerate(order, start=1):
            target_x = rect.x + 282 + (execution_index - 1) * 78
            if flipping:
                old_index = old_order.index(slot)
                origin_x = rect.x + 282 + old_index * 78
                eased = 1 - (1 - app.presentation.progress) ** 3
                chip_x = round(origin_x + (target_x - origin_x) * eased)
            else:
                chip_x = target_x
            chip = pygame.Rect(chip_x, rect.y + 7, 56, 34)
            active = active_tick == execution_index
            pygame.draw.rect(self.screen, color if active else COLORS["surface_high"], chip, border_radius=8)
            pygame.draw.rect(self.screen, COLORS["text"] if active else color, chip, 2, border_radius=8)
            self._center(str(slot), 16, COLORS["background"] if active else COLORS["text"], chip.center, True)
            if execution_index < 3 and not flipping:
                self._center("→", 16, color, (chip.right + 11, chip.centery), True)

    @staticmethod
    def _display_rule(app: Any, final_rule: TimelineRule) -> TimelineRule:
        frame = app.presentation
        if frame.event_index is None:
            return final_rule
        visible = [event for event in app.events if event.kind != "waited"]
        displayed = final_rule
        for event in visible[: frame.event_index + 1]:
            if event.kind in {"rule_triggered", "rule_changed", "rule_held"}:
                try:
                    displayed = TimelineRule(event.detail)
                except ValueError:
                    pass
        return displayed

    def _draw_event_strip(self, app: Any) -> None:
        if app.tutorial.current is not None:
            self._tutorial_panel(app)
            return
        rect = pygame.Rect(48, 626, 576, 126)
        self._panel(rect, COLORS["border"])
        self._text_at("因果反馈", 14, COLORS["primary"], (rect.x + 14, rect.y + 10), True)
        visible = [event for event in app.events if event.kind != "waited"][-3:]
        for index, event in enumerate(visible):
            marker = COLORS["danger"] if event.kind in {"damaged", "died"} else COLORS["success"] if event.kind in {"intent_cancelled", "plugin_triggered"} else COLORS["primary"]
            pygame.draw.circle(self.screen, marker, (rect.x + 20, rect.y + 46 + index * 25), 4)
            readable_detail = event_detail_label(event, app.battle_view)
            detail = f" / {readable_detail}" if readable_detail else ""
            self._text_at(f"t{event.tick}  {EVENT_LABELS.get(event.kind, '战术事件')}{detail}", 13, COLORS["text"], (rect.x + 34, rect.y + 36 + index * 25))

    def _execution_overlay(self, app: Any) -> None:
        if not app.execution_active:
            return
        phase = app.execution_phase
        if phase == "prepare":
            rect = pygame.Rect(190, 284, 292, 64)
            self._panel(rect, COLORS["primary"], True)
            self._center("EXECUTION ARMED", 17, COLORS["text"], (rect.centerx, rect.y + 23), True, "data")
            self._center("准备因果链路", 12, COLORS["primary"], (rect.centerx, rect.y + 45), True)
        elif phase == "result":
            self._center("RESULT / 因果结算完成", 13, COLORS["primary"], (336, 594), True, "data")
        elif app.causality_rewrite_visible:
            if app.ui.reduced_motion:
                progress = app.causality_rewrite_progress
                alpha = round(255 * (1 - abs(progress * 2 - 1)))
                layer = pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)
                layer.fill((7, 10, 18, round(alpha * 0.48)))
                rect = pygame.Rect(150, 292, 372, 116)
                pygame.draw.rect(layer, (*COLORS["surface_high"], alpha), rect, border_radius=10)
                pygame.draw.rect(layer, (*COLORS["primary"], alpha), rect, 3, border_radius=10)
                title = self._surface("CAUSALITY REWRITTEN", 23, COLORS["text"], True, "display").copy()
                subtitle = self._surface("因果已改写", 16, COLORS["primary"], True).copy()
                title.set_alpha(alpha)
                subtitle.set_alpha(alpha)
                layer.blit(title, title.get_rect(center=(rect.centerx, rect.y + 41)))
                layer.blit(subtitle, subtitle.get_rect(center=(rect.centerx, rect.y + 78)))
                self.screen.blit(layer, (0, 0))
                return
            overlay = pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)
            overlay.fill((7, 10, 18, 142))
            if not app.ui.reduced_motion:
                scan_y = 238 + (pygame.time.get_ticks() // 5) % 210
                pygame.draw.line(overlay, (*COLORS["primary"], 180), (84, scan_y), (588, scan_y), 2)
                for offset in (0, 9, 23):
                    x = 120 + ((pygame.time.get_ticks() // 4 + offset * 31) % 390)
                    pygame.draw.line(overlay, (*COLORS["primary"], 76), (x, 274), (x + 42, 274), 2)
            self.screen.blit(overlay, (0, 0))
            rect = pygame.Rect(150, 292, 372, 116)
            self._panel(rect, COLORS["primary"], True)
            self._center("CAUSALITY REWRITTEN", 23, COLORS["text"], (rect.centerx, rect.y + 41), True, "display")
            self._center("因果已改写", 16, COLORS["primary"], (rect.centerx, rect.y + 78), True)

    def _reward(self, app: Any) -> None:
        run = app.level_run
        self._center("PROTOCOL SELECTION", 16, COLORS["violet"], (640, 84), True, "data")
        self._center("选择一次规则改写", 38, COLORS["text"], (640, 134), True)
        self._center("不是加分词条：你的下一组三拍会产生不同结果", 17, COLORS["muted"], (640, 184))
        build = " / ".join(
            definition.display_name + (f"×{stacks}" if stacks > 1 else "")
            for definition, stacks in run.build_summary
        ) or "尚未安装"
        self._center(f"当前 Build：{build}   ·   Seed {run.run_seed}", 14, COLORS["violet"], (640, 214), True)
        for index, (plugin, rect) in enumerate(zip(run.reward_choices, REWARD_RECTS, strict=True)):
            focused = index == app.ui.reward_focus
            draw_rect = rect.inflate(10, 10) if focused and app.reward_acquisition is None else rect
            self._panel(draw_rect, COLORS["violet"] if focused else COLORS["border"], focused)
            if focused:
                glow = draw_rect.inflate(10, 10)
                pygame.draw.rect(self.screen, COLORS["violet_dark"], glow, 2, border_radius=14)
                badge = pygame.Rect(draw_rect.centerx - 48, draw_rect.y - 9, 96, 22)
                pygame.draw.rect(self.screen, COLORS["violet"], badge, border_radius=10)
                self._center("SELECTED", 11, COLORS["background"], badge.center, True)
            self._center(f"0{index + 1}", 14, COLORS["violet"], (draw_rect.centerx, draw_rect.y + 32), True, "data")
            self._protocol_icon(plugin.plugin_id, (draw_rect.centerx, draw_rect.y + 88))
            type_label = "CORE PROTOCOL" if plugin.plugin_id in {"echo_protocol", "kinetic_amplifier", "emergency_barrier"} else "SYNERGY MODULE" if plugin.requirements else "TACTICAL MODULE"
            self._center(type_label, 10, COLORS["violet"], (draw_rect.centerx, draw_rect.y + 126), True, "data")
            self._center(plugin.display_name, 24, COLORS["text"], (draw_rect.centerx, draw_rect.y + 158), True)
            self._center(" · ".join(plugin.tags), 13, COLORS["violet"], (draw_rect.centerx, draw_rect.y + 183), True)
            relation = self._build_relation(plugin, run)
            self._center(relation, 13, COLORS["violet"], (draw_rect.centerx, draw_rect.y + 207), True)
            self._wrapped(
                plugin.description,
                13,
                COLORS["muted"],
                pygame.Rect(draw_rect.x + 30, draw_rect.y + 228, draw_rect.width - 60, 48),
                19,
            )
            self._center(f"{index + 1}  安装协议" if not focused else "ENTER  确认安装", 15, COLORS["primary"], (draw_rect.centerx, draw_rect.bottom - 32), True)
        self._center("← / → 或鼠标选择   ·   ENTER 确认", 14, COLORS["muted"], (640, 618))
        if app.reward_acquisition is not None:
            self._reward_acquired_overlay(app)

    def _reward_acquired_overlay(self, app: Any) -> None:
        plugin = app.reward_acquisition
        progress = app.reward_animation_progress
        overlay = pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)
        overlay.fill((7, 10, 18, round(190 * min(1.0, progress * 2))))
        self.screen.blit(overlay, (0, 0))
        selected = REWARD_RECTS[app.ui.reward_focus].center
        if app.ui.reduced_motion:
            center = (640, 330)
        else:
            eased = 1 - (1 - progress) ** 3
            target = PROTOCOL_RECT.center
            center = (
                round(selected[0] + (target[0] - selected[0]) * eased),
                round(selected[1] + (target[1] - selected[1]) * eased),
            )
        if progress < 0.72 or app.ui.reduced_motion:
            self._protocol_icon(plugin.plugin_id, center, 34)
        if progress < 0.78:
            rect = pygame.Rect(390, 258, 500, 154)
            self._panel(rect, COLORS["violet"], True)
            self._center("PROTOCOL ACQUIRED", 15, COLORS["violet"], (rect.centerx, rect.y + 34), True, "data")
            self._center(plugin.display_name, 30, COLORS["text"], (rect.centerx, rect.y + 78), True, "display")
            self._center(protocol_code(plugin.plugin_id), 12, COLORS["violet"], (rect.centerx, rect.y + 116), True, "data")

    def _result(self, app: Any) -> None:
        clear = app.level_run.phase is LevelPhase.LEVEL_CLEAR
        color = COLORS["success"] if clear else COLORS["danger"]
        for radius in (108, 88, 70):
            self._diamond((640, 206), radius, color if radius == 70 else COLORS["border"], 4 if radius == 70 else 2)
        pygame.draw.circle(self.screen, COLORS["text"], (640, 206), 8)
        self._center("ECHO // ZERO", 15, color, (640, 300), True)
        self._center("CAUSALITY SECURED" if clear else "SYSTEM FAILURE", 42, COLORS["text"], (640, 340), True, "display")
        subtitle = (
            "逆相反应堆已稳定，两关协议链路全部通过。"
            if clear
            else f"核心离线于 {app.level_run.current_definition.title}；根据 Preview 调整三拍后重试。"
        )
        self._center(subtitle, 18, COLORS["muted"], (640, 400))
        plugins = " / ".join(
            definition.display_name + (f"×{stacks}" if stacks > 1 else "")
            for definition, stacks in app.level_run.build_summary
        ) or "无"
        encounter_text = "6 / 6 ENCOUNTERS" if clear else f"LEVEL {app.level_index + 1:02} INTERRUPTED"
        self._center(f"{encounter_text}   ·   RUN SEED {app.level_run.run_seed}", 14, color, (640, 452), True)
        self._center(f"FINAL BUILD   {plugins}", 16, COLORS["violet"], (640, 490), True)
        self._button(RESULT_RESTART_RECT, "再次校准完整链路  [ENTER / R]", True)
        self._center("ESC 退出", 13, COLORS["muted"], (640, 686))

    def _transition(self, app: Any) -> None:
        pulse = 0 if app.ui.reduced_motion else (pygame.time.get_ticks() // 80) % 9
        self._diamond((640, 190), 64 + pulse, COLORS["violet"], 4)
        self._center("LEVEL 01 CLEAR", 18, COLORS["success"], (640, 292), True)
        self._center("逆相反应堆", 44, COLORS["text"], (640, 354), True)
        self._center("TIMELINE RULE OVERRIDE", 13, COLORS["violet"], (640, 404), True)
        self._center("1  →  2  →  3    // SWITCH //    3  →  2  →  1", 21, COLORS["warning"], (640, 438), True)
        build = " / ".join(
            definition.display_name + (f"×{stacks}" if stacks > 1 else "")
            for definition, stacks in app.level_run.build_summary
        )
        self._center(f"Build 继承：{build}", 15, COLORS["violet"], (640, 486), True)
        self._button(RESULT_RESTART_RECT, "进入 Level 2  [ENTER]", True)

    def _rule_overlay(self, app: Any) -> None:
        event = app.presentation.event
        if event is None or event.kind not in {"rule_triggered", "rule_changed", "rule_held"}:
            return
        if event.kind == "rule_held":
            title, subtitle, color = "PHASE ANCHOR LOCK", "相位锚已激活 · 下一回合规则保持", COLORS["success"]
        else:
            reverse = event.detail == TimelineRule.REVERSE.value
            title = "INVERSE // 3 → 2 → 1" if reverse else "STABLE // 1 → 2 → 3"
            subtitle = "执行顺序已改写" if event.kind == "rule_changed" else "本回合按逆相顺序执行"
            color = COLORS["violet"] if reverse else COLORS["primary"]
        rect = pygame.Rect(188, 292, 400, 92)
        self._panel(rect, color, True)
        self._center(title, 20, COLORS["text"], (rect.centerx, rect.y + 31), True)
        self._center(subtitle, 13, color, (rect.centerx, rect.y + 64), True)

    def _error(self, message: str) -> None:
        self._center("CONTENT LOAD FAILED", 32, COLORS["danger"], (640, 240), True)
        self._wrapped("战术数据无法校验，程序未进入战斗。", 17, COLORS["text"], pygame.Rect(240, 300, 800, 160), 30, centered=True)
        self._center("请重新启动；若问题持续，请检查本地资源完整性。", 15, COLORS["muted"], (640, 510))

    def _protocol_icon(self, plugin_id: str, center: tuple[int, int], radius: int = 28) -> None:
        color = COLORS["violet"]
        if plugin_id == "echo_protocol":
            pygame.draw.arc(self.screen, color, pygame.Rect(center[0] - radius, center[1] - radius, radius * 2, radius * 2), 0.4, 5.7, max(2, radius // 7))
            pygame.draw.circle(self.screen, color, center, max(3, radius // 3), max(2, radius // 9))
        elif plugin_id == "kinetic_amplifier":
            pygame.draw.polygon(self.screen, color, [(center[0] - radius, center[1] - radius + 4), (center[0] + radius // 5, center[1]), (center[0] - radius, center[1] + radius - 4)], max(2, radius // 7))
            pygame.draw.line(self.screen, color, (center[0] + radius // 6, center[1]), (center[0] + radius, center[1]), max(2, radius // 7))
        else:
            self._diamond(center, radius, color, max(2, radius // 7))
            pygame.draw.line(self.screen, color, (center[0] - radius * 2 // 3, center[1]), (center[0] + radius * 2 // 3, center[1]), max(2, radius // 9))

    def _panel(self, rect: pygame.Rect, border: tuple[int, int, int], strong: bool = False) -> None:
        pygame.draw.rect(self.screen, COLORS["surface_high"] if strong else COLORS["surface"], rect, border_radius=10)
        pygame.draw.rect(self.screen, border, rect, 3 if strong else 1, border_radius=10)

    def _button(self, rect: pygame.Rect, label: str, primary: bool) -> None:
        fill = COLORS["primary_dark"] if primary else COLORS["surface"]
        border = COLORS["primary"] if primary else COLORS["border"]
        pygame.draw.rect(self.screen, fill, rect, border_radius=10)
        pygame.draw.rect(self.screen, border, rect, 2, border_radius=10)
        self._center(label, 18, COLORS["text"], rect.center, True)

    def _diamond(self, center: tuple[int, int], radius: int, color: tuple[int, int, int], width: int) -> None:
        points = [(center[0], center[1] - radius), (center[0] + radius, center[1]), (center[0], center[1] + radius), (center[0] - radius, center[1])]
        pygame.draw.polygon(self.screen, color, points, width)

    @staticmethod
    def cell_rect(pos: GridPos) -> pygame.Rect:
        return pygame.Rect(GRID_ORIGIN[0] + pos.x * CELL_SIZE, GRID_ORIGIN[1] + pos.y * CELL_SIZE, CELL_SIZE, CELL_SIZE)

    def _font(self, size: int, bold: bool = False, role: str = "body") -> pygame.font.Font:
        key = (size, bold, role)
        if key not in self.fonts:
            families = {
                "display": "bahnschriftsemibold,microsoftyahei,simhei,arial",
                "data": "microsoftyahei,simhei,cascadiamono,consolas",
                "body": "microsoftyahei,simhei,segoeui,arial",
            }
            name = pygame.font.match_font(families.get(role, families["body"]))
            self.fonts[key] = pygame.font.Font(name, size)
            self.fonts[key].bold = bold
        return self.fonts[key]

    def _surface(self, text: str, size: int, color: tuple[int, int, int], bold: bool = False, role: str = "body") -> pygame.Surface:
        key = (text, size, color, bold, role)
        if key not in self.text_cache:
            self.text_cache[key] = self._font(size, bold, role).render(text, True, color)
        return self.text_cache[key]

    def _global_status(self, app: Any) -> None:
        audio = "静音" if app.ui.muted else "音频"
        motion = "减弱动态" if app.ui.reduced_motion else "完整动态"
        self._text_at("ESC 退出   ·   TAB 教学下一条   ·   F1 跳过教学", 12, COLORS["muted"], (48, 776))
        self._text_at(f"M {audio}  {app.ui.volume_percent}%   ·   -/+ 音量   ·   F2 {motion}", 12, COLORS["muted"], (872, 776))

    def _tutorial_panel(self, app: Any) -> None:
        step = app.tutorial.current
        if step is None:
            return
        rect = pygame.Rect(48, 626, 576, 126)
        self._panel(rect, COLORS["warning"], True)
        level_one = ("timeline", "input", "intent", "preview", "execute")
        level_two = ("level2_order", "anchor", "phase_switch")
        group = level_one if step.step_id in level_one else level_two
        current = group.index(step.step_id) + 1
        total = len(group)
        self._text_at(
            f"GUIDE  {current}/{total}   {step.title}",
            14,
            COLORS["warning"],
            (rect.x + 14, rect.y + 10),
            True,
        )
        self._text_at(step.body, 13, COLORS["muted"], (rect.x + 14, rect.y + 39))
        self._button(TUTORIAL_NEXT_RECT, "下一条  [TAB]", True)
        self._button(TUTORIAL_SKIP_RECT, "跳过全部  [F1]", False)

    def _tutorial_highlight(self, app: Any) -> None:
        step = app.tutorial.current
        if step is None:
            return
        rects: list[pygame.Rect] = []
        if step.target == "slots":
            rects.append(SLOT_RECTS[0].unionall(SLOT_RECTS[1:]))
        elif step.target == "intent":
            rects.append(INTENT_RECT)
        elif step.target == "preview":
            rects.append(PREVIEW_RECT)
        elif step.target == "execute":
            rects.append(EXECUTE_RECT)
        elif step.target == "rule":
            rects.append(TIMELINE_RECT)
        elif step.target == "anchor":
            rects.extend(
                self.cell_rect(node).inflate(-4, -4)
                for node in app.level_run.encounter.state.rule_nodes
            )
        for rect in rects:
            pygame.draw.rect(
                self.screen,
                COLORS["warning"],
                rect.inflate(8, 8),
                3,
                border_radius=12,
            )

    @staticmethod
    def _build_relation(plugin: Any, run: Any) -> str:
        if plugin.requirements:
            names = [
                run.plugin_definitions[item].display_name
                for item in plugin.requirements
            ]
            return "联动就绪  " + " + ".join(names)
        if plugin.plugin_id in {
            "echo_protocol",
            "kinetic_amplifier",
            "emergency_barrier",
        }:
            return f"路线核心  ·  {plugin.tags[0]}"
        active_tags = {
            tag
            for definition, _ in run.build_summary
            for tag in definition.tags
        }
        shared = [tag for tag in plugin.tags if tag in active_tags]
        return "关键词呼应  ·  " + " / ".join(shared) if shared else "独立策略分支"

    def _text_at(self, text: str, size: int, color: tuple[int, int, int], pos: tuple[int, int], bold: bool = False, role: str = "body") -> None:
        self.screen.blit(self._surface(text, size, color, bold, role), pos)

    def _center(self, text: str, size: int, color: tuple[int, int, int], center: tuple[int, int], bold: bool = False, role: str = "body") -> None:
        surface = self._surface(text, size, color, bold, role)
        self.screen.blit(surface, surface.get_rect(center=center))

    def _wrapped(self, text: str, size: int, color: tuple[int, int, int], rect: pygame.Rect, line_height: int, centered: bool = False) -> None:
        lines: list[str] = []
        line = ""
        for char in text:
            candidate = line + char
            if line and self._surface(candidate, size, color).get_width() > rect.width:
                lines.append(line)
                line = char
            else:
                line = candidate
        if line:
            lines.append(line)
        for index, value in enumerate(lines):
            surface = self._surface(value, size, color)
            target = surface.get_rect(midtop=(rect.centerx, rect.y + index * line_height)) if centered else surface.get_rect(topleft=(rect.x, rect.y + index * line_height))
            self.screen.blit(surface, target)
