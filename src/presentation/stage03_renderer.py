"""Formal Stage03 pygame renderer. It only reads domain state and logic events."""

from __future__ import annotations

from typing import Any

import pygame

from src.domain import Command, CommandType, Faction, GridPos, LevelPhase, LogicEvent, TimelineRule
from src.presentation.effects import MOVEMENT_KINDS, plugin_feedback

WINDOW_SIZE = (1280, 800)
CELL_SIZE = 72
GRID_ORIGIN = (48, 174)
PANEL_X = 664
SLOT_RECTS = tuple(pygame.Rect(PANEL_X, 306 + index * 78, 568, 64) for index in range(3))
EXECUTE_RECT = pygame.Rect(PANEL_X, 558, 370, 58)
RESTART_RECT = pygame.Rect(1050, 558, 182, 58)
MENU_START_RECT = pygame.Rect(460, 568, 360, 64)
REWARD_RECTS = tuple(pygame.Rect(96 + index * 376, 260, 336, 300) for index in range(3))
RESULT_RESTART_RECT = pygame.Rect(448, 586, 384, 62)

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
        self.screen = pygame.Surface(screen.get_size())
        self.fonts: dict[tuple[int, bool], pygame.font.Font] = {}
        self.text_cache: dict[tuple[str, int, tuple[int, int, int], bool], pygame.Surface] = {}

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
        self.output.blit(self.screen, shake)

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
        self._center("TACTICAL CAUSALITY // TWO-LEVEL DEMO", 13, COLORS["muted"], (640, 72), True)
        for radius, alpha_color in ((116, COLORS["primary_dark"]), (96, COLORS["violet_dark"])):
            self._diamond((640, 222), radius, alpha_color, 2)
        self._diamond((640, 222), 82, COLORS["primary"], 4)
        self._diamond((640, 222), 52, COLORS["violet"], 2)
        pygame.draw.circle(self.screen, COLORS["text"], (640, 222), 10)
        self._center("ECHO // ZERO", 54, COLORS["text"], (640, 344), True)
        self._center("CALIBRATION // INVERSE REACTOR", 18, COLORS["primary"], (640, 398), True)
        self._center("编排三拍 · 看见因果 · 改写结果", 22, COLORS["muted"], (640, 452))
        self._button(MENU_START_RECT, "开始校准  [ENTER]", True)
        self._center("双关卡  /  六场短遭遇  /  Build 继承  /  逆相终局", 15, COLORS["muted"], (640, 674))

    def _battle(self, app: Any) -> None:
        run = app.level_run
        encounter = run.encounter
        definition = run.current_definition
        current, total = run.progress
        self._text_at("ECHO // ZERO", 22, COLORS["text"], (48, 28), True)
        level_color = COLORS["violet"] if app.level_index == 1 else COLORS["primary"]
        self._text_at(f"LEVEL {app.level_index + 1:02}  {run.definition.display_name}", 14, level_color, (48, 61), True)
        self._progress(current, total)
        self._text_at(definition.title, 26, COLORS["text"], (48, 105), True)
        self._text_at(definition.objective, 16, COLORS["muted"], (48, 139))
        self._draw_board(app)
        self._draw_hud(app)
        self._draw_event_strip(app)
        self._rule_overlay(app)

    def _progress(self, current: int, total: int) -> None:
        start_x = 950
        for index in range(total):
            center = (start_x + index * 92, 48)
            color = COLORS["primary"] if index < current else COLORS["border"]
            if index:
                pygame.draw.line(self.screen, COLORS["border"], (center[0] - 76, 48), (center[0] - 16, 48), 2)
            pygame.draw.circle(self.screen, color, center, 11, 3)
            if index < current - 1:
                pygame.draw.circle(self.screen, color, center, 5)
            self._center(str(index + 1), 12, COLORS["text"], (center[0], 76), True)

    def _draw_board(self, app: Any) -> None:
        state = app.level_run.encounter.state
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
            pygame.draw.rect(self.screen, COLORS["danger_dark"], target, border_radius=10)
            pygame.draw.rect(self.screen, COLORS["danger"], target, 3, border_radius=10)
            for offset in range(-target.height, target.width, 14):
                pygame.draw.line(self.screen, (127, 41, 65), (target.x + offset, target.bottom), (target.x + offset + target.height, target.top), 1)
            actor = state.entities.get(intent.actor_id)
            if actor is not None:
                pygame.draw.line(self.screen, COLORS["danger"], self.cell_rect(actor.pos).center, target.center, 2)
            self._center(f"! {intent.order}", 15, COLORS["text"], target.center, True)
        for event in app.preview.events:
            if event.tick <= 3 and event.to_pos is not None and event.kind in {"moved", "pulled", "pushed"}:
                center = self.cell_rect(event.to_pos).center
                pygame.draw.circle(self.screen, COLORS["primary"], center, 18, 2)
                self._center(str(event.tick), 13, COLORS["primary"], center, True)
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
                self._entity(entity, flash=flash)
        if active is not None:
            effect_pos = active.to_pos
            actor = state.entities.get(active.actor_id)
            if effect_pos is None and active.kind == "shielded" and actor is not None:
                effect_pos = actor.pos
            if effect_pos is not None:
                self._event_effect(active, effect_pos, frame.progress)
        if anchored:
            self._text_at("PHASE LOCKED // 规则保持", 13, COLORS["success"], (48, 590), True)

    def _entity(self, entity: Any, center: tuple[int, int] | None = None, flash: bool = False) -> None:
        rect = self.cell_rect(entity.pos).inflate(-14, -14)
        center = center or rect.center
        color_override = COLORS["text"] if flash else None
        if entity.faction is Faction.PLAYER:
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
            color = COLORS["violet"] if entity.enemy_kind == "sweeper" else COLORS["warning"]
            self._diamond(center, 27, color, 4)
            pygame.draw.line(self.screen, color, (center[0] - 29, center[1]), (center[0] + 29, center[1]), 4)
            pygame.draw.circle(self.screen, COLORS["danger"], center, 7)
        else:
            points = [(center[0] + 25, center[1]), (center[0] + 12, center[1] + 22), (center[0] - 12, center[1] + 22), (center[0] - 25, center[1]), (center[0] - 12, center[1] - 22), (center[0] + 12, center[1] - 22)]
            pygame.draw.polygon(self.screen, COLORS["warning"], points, 4)
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
        color = COLORS["danger"] if event.kind in {"damaged", "died", "push_blocked"} else COLORS["warning"]
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
        run = app.level_run
        encounter = run.encounter
        player = encounter.state.entities.get("player")
        hp = "--" if player is None else f"{player.hp}/{player.max_hp}"
        self._text_at(f"CORE  {hp}", 18, COLORS["text"], (PANEL_X, 108), True)
        plugin_names = [
            definition.display_name + (f"×{stacks}" if stacks > 1 else "")
            for definition, stacks in run.build_summary
        ]
        self._text_at("协议  " + (" / ".join(plugin_names) if plugin_names else "尚未安装"), 14, COLORS["violet"], (PANEL_X + 180, 111), True)
        intent_rect = pygame.Rect(PANEL_X, 146, 568, 92)
        self._panel(intent_rect, COLORS["danger"] if encounter.state.enemy_intents else COLORS["border"])
        self._text_at("公开意图", 15, COLORS["danger"], (intent_rect.x + 16, intent_rect.y + 12), True)
        intents = encounter.state.enemy_intents
        if not intents:
            self._text_at("SAFE  当前没有可执行的锁定攻击", 14, COLORS["success"], (intent_rect.x + 16, intent_rect.y + 46), True)
        else:
            by_actor: dict[str, list[Any]] = {}
            for item in intents:
                by_actor.setdefault(item.actor_id, []).append(item)
            lines = []
            for actor_id, items in by_actor.items():
                actor = encounter.state.entities.get(actor_id)
                kind = ENEMY_LABELS.get(getattr(actor, "enemy_kind", ""), "攻击")
                cells = " / ".join(f"({item.target_pos.x},{item.target_pos.y})" for item in items)
                lines.append(f"{kind}  目标 {cells}  ·  伤害 {items[0].damage}  ·  敌方阶段")
            for index, line in enumerate(lines[:2]):
                self._text_at(line, 13, COLORS["text"], (intent_rect.x + 16, intent_rect.y + 40 + index * 23), True)
        rule = self._display_rule(app, encounter.state.active_timeline_rule)
        self._timeline_bar(app, rule)
        for index, (command, rect) in enumerate(zip(encounter.commands, SLOT_RECTS, strict=True)):
            selected = app.ui.selected_slot == index
            execution_tick = 3 - index if rule is TimelineRule.REVERSE else index + 1
            active_tick = app.presentation.event.tick if app.presentation.event is not None else -1
            is_executing = active_tick == execution_tick
            self._panel(rect, COLORS["warning"] if is_executing else COLORS["primary"] if selected else COLORS["border"], selected or is_executing)
            badge = pygame.Rect(rect.x + 10, rect.y + 10, 44, 44)
            pygame.draw.rect(self.screen, COLORS["violet_dark"] if rule is TimelineRule.REVERSE else COLORS["primary_dark"], badge, border_radius=8)
            self._center(str(index + 1), 18, COLORS["primary"], badge.center, True)
            self._text_at(app.command_label(command), 17, COLORS["text"], (rect.x + 70, rect.y + 8), True)
            self._text_at(f"执行第 {execution_tick} 拍  ·  {app.preview_label(execution_tick)}", 13, COLORS["muted"], (rect.x + 70, rect.y + 36))
        self._button(EXECUTE_RECT, "确认执行  [ENTER]", True)
        self._button(RESTART_RECT, "重启 Demo  [R]", False)
        preview = app.preview.state
        preview_player = preview.entities.get("player")
        enemy_count = sum(entity.faction is Faction.ENEMY for entity in preview.entities.values())
        prediction = f"预演终态  CORE {preview_player.hp if preview_player else 0}  /  威胁 {enemy_count}"
        self._text_at(prediction, 15, COLORS["success"] if preview_player else COLORS["danger"], (PANEL_X, 638), True)
        self._text_at(run.current_definition.hint, 14, COLORS["warning"], (PANEL_X, 670))
        self._text_at(app.ui.feedback, 13, COLORS["muted"], (PANEL_X, 702))
        if app.ui.debug:
            self._text_at(f"seed={run.run_seed}  turn={encounter.state.turn}  events={len(app.events)}  preview={'PASS' if app.ui.verification_ok is not False else 'FAIL'}", 12, COLORS["muted"], (PANEL_X, 756))
        banner = plugin_feedback(app.presentation.event)
        if banner:
            rect = pygame.Rect(120, 116, 408, 46)
            self._panel(rect, COLORS["violet"], True)
            self._center(f"◆  BUILD ONLINE  //  {banner}", 14, COLORS["text"], rect.center, True)

    def _timeline_bar(self, app: Any, rule: TimelineRule) -> None:
        rect = pygame.Rect(PANEL_X, 246, 568, 48)
        inverse = rule is TimelineRule.REVERSE
        color = COLORS["violet"] if inverse else COLORS["primary"]
        self._panel(rect, color, inverse)
        self._text_at("逆相执行" if inverse else "稳定执行", 14, color, (rect.x + 14, rect.y + 14), True)
        order = (3, 2, 1) if inverse else (1, 2, 3)
        active_tick = app.presentation.event.tick if app.presentation.event is not None else -1
        for execution_index, slot in enumerate(order, start=1):
            chip = pygame.Rect(rect.x + 282 + (execution_index - 1) * 78, rect.y + 7, 56, 34)
            active = active_tick == execution_index
            pygame.draw.rect(self.screen, color if active else COLORS["surface_high"], chip, border_radius=8)
            pygame.draw.rect(self.screen, COLORS["text"] if active else color, chip, 2, border_radius=8)
            self._center(str(slot), 16, COLORS["background"] if active else COLORS["text"], chip.center, True)
            if execution_index < 3:
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
        rect = pygame.Rect(48, 626, 576, 126)
        self._panel(rect, COLORS["border"])
        self._text_at("因果反馈", 14, COLORS["primary"], (rect.x + 14, rect.y + 10), True)
        visible = [event for event in app.events if event.kind != "waited"][-3:]
        for index, event in enumerate(visible):
            marker = COLORS["danger"] if event.kind in {"damaged", "died"} else COLORS["success"] if event.kind in {"intent_cancelled", "plugin_triggered"} else COLORS["primary"]
            pygame.draw.circle(self.screen, marker, (rect.x + 20, rect.y + 46 + index * 25), 4)
            detail = f" / {event.detail}" if event.detail else ""
            self._text_at(f"t{event.tick}  {EVENT_LABELS.get(event.kind, event.kind)}{detail}", 13, COLORS["text"], (rect.x + 34, rect.y + 36 + index * 25))

    def _reward(self, app: Any) -> None:
        run = app.level_run
        self._center("PROTOCOL ACQUIRED", 16, COLORS["primary"], (640, 84), True)
        self._center("选择一次规则改写", 38, COLORS["text"], (640, 134), True)
        self._center("不是加分词条：你的下一组三拍会产生不同结果", 17, COLORS["muted"], (640, 184))
        build = " / ".join(
            definition.display_name + (f"×{stacks}" if stacks > 1 else "")
            for definition, stacks in run.build_summary
        ) or "尚未安装"
        self._center(f"当前 Build：{build}   ·   Seed {run.run_seed}", 14, COLORS["violet"], (640, 214), True)
        for index, (plugin, rect) in enumerate(zip(run.reward_choices, REWARD_RECTS, strict=True)):
            focused = index == app.ui.reward_focus
            self._panel(rect, COLORS["primary"] if focused else COLORS["border"], focused)
            if focused:
                badge = pygame.Rect(rect.centerx - 48, rect.y - 9, 96, 22)
                pygame.draw.rect(self.screen, COLORS["primary"], badge, border_radius=10)
                self._center("SELECTED", 11, COLORS["background"], badge.center, True)
            self._center(f"0{index + 1}", 14, COLORS["primary"], (rect.centerx, rect.y + 32), True)
            self._protocol_icon(plugin.plugin_id, (rect.centerx, rect.y + 92))
            self._center(plugin.display_name, 24, COLORS["text"], (rect.centerx, rect.y + 154), True)
            self._center(" · ".join(plugin.tags), 13, COLORS["violet"], (rect.centerx, rect.y + 180), True)
            self._wrapped(plugin.description, 15, COLORS["muted"], pygame.Rect(rect.x + 30, rect.y + 202, rect.width - 60, 78), 24)
            self._center(f"{index + 1}  安装协议" if not focused else "ENTER  确认安装", 15, COLORS["primary"], (rect.centerx, rect.bottom - 32), True)
        self._center("← / → 或鼠标选择   ·   ENTER 确认", 14, COLORS["muted"], (640, 618))

    def _result(self, app: Any) -> None:
        clear = app.level_run.phase is LevelPhase.LEVEL_CLEAR
        color = COLORS["success"] if clear else COLORS["danger"]
        for radius in (108, 88, 70):
            self._diamond((640, 206), radius, color if radius == 70 else COLORS["border"], 4 if radius == 70 else 2)
        pygame.draw.circle(self.screen, COLORS["text"], (640, 206), 8)
        self._center("ECHO // ZERO", 15, color, (640, 300), True)
        self._center("DEMO CLEAR" if clear else "SYSTEM FAILURE", 46, COLORS["text"], (640, 340), True)
        subtitle = "逆相反应堆已稳定，两关协议链路全部通过。" if clear else "核心离线。重新开始后可再次构筑。"
        self._center(subtitle, 18, COLORS["muted"], (640, 400))
        plugins = " / ".join(
            definition.display_name + (f"×{stacks}" if stacks > 1 else "")
            for definition, stacks in app.level_run.build_summary
        ) or "无"
        encounter_text = "6 / 6 ENCOUNTERS" if clear else f"LEVEL {app.level_index + 1:02} INTERRUPTED"
        self._center(f"{encounter_text}   ·   RUN SEED {app.level_run.run_seed}", 14, color, (640, 452), True)
        self._center(f"FINAL BUILD   {plugins}", 16, COLORS["violet"], (640, 490), True)
        self._button(RESULT_RESTART_RECT, "重新开始完整 Demo  [ENTER / R]", True)
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
        self._wrapped(message, 17, COLORS["text"], pygame.Rect(240, 300, 800, 160), 30, centered=True)
        self._center("请检查 data/levels 与 data/plugins 配置后重新启动。", 15, COLORS["muted"], (640, 510))

    def _protocol_icon(self, plugin_id: str, center: tuple[int, int]) -> None:
        color = COLORS["violet"]
        if plugin_id == "echo_protocol":
            pygame.draw.arc(self.screen, color, pygame.Rect(center[0] - 30, center[1] - 30, 60, 60), 0.4, 5.7, 4)
            pygame.draw.circle(self.screen, color, center, 9, 3)
        elif plugin_id == "kinetic_amplifier":
            pygame.draw.polygon(self.screen, color, [(center[0] - 28, center[1] - 24), (center[0] + 5, center[1]), (center[0] - 28, center[1] + 24)], 4)
            pygame.draw.line(self.screen, color, (center[0] + 3, center[1]), (center[0] + 31, center[1]), 4)
        else:
            self._diamond(center, 28, color, 4)
            pygame.draw.line(self.screen, color, (center[0] - 18, center[1]), (center[0] + 18, center[1]), 3)

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

    def _font(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in self.fonts:
            name = pygame.font.match_font("microsoftyahei,simhei,consolas,arial")
            self.fonts[key] = pygame.font.Font(name, size)
            self.fonts[key].bold = bold
        return self.fonts[key]

    def _surface(self, text: str, size: int, color: tuple[int, int, int], bold: bool = False) -> pygame.Surface:
        key = (text, size, color, bold)
        if key not in self.text_cache:
            self.text_cache[key] = self._font(size, bold).render(text, True, color)
        return self.text_cache[key]

    def _global_status(self, app: Any) -> None:
        audio = "静音" if app.ui.muted else "音频"
        motion = "减弱动态" if app.ui.reduced_motion else "完整动态"
        self._text_at(f"M {audio}  {app.ui.volume_percent}%   ·   -/+ 音量   ·   F2 {motion}   ·   F3 调试{'开' if app.ui.debug else '关'}", 12, COLORS["muted"], (800, 776))

    def _text_at(self, text: str, size: int, color: tuple[int, int, int], pos: tuple[int, int], bold: bool = False) -> None:
        self.screen.blit(self._surface(text, size, color, bold), pos)

    def _center(self, text: str, size: int, color: tuple[int, int, int], center: tuple[int, int], bold: bool = False) -> None:
        surface = self._surface(text, size, color, bold)
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
