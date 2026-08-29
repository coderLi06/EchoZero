"""Formal Stage03 pygame renderer. It only reads domain state and logic events."""

from __future__ import annotations

from typing import Any

import pygame

from src.domain import Command, CommandType, Faction, GridPos, LevelPhase, LogicEvent

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
}


class Stage03Renderer:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.fonts: dict[tuple[int, bool], pygame.font.Font] = {}

    def draw(self, app: Any) -> None:
        self._background()
        scene = app.scene.value
        if scene == "menu":
            self._menu()
        elif scene == "battle":
            self._battle(app)
        elif scene == "reward":
            self._reward(app)
        elif scene == "result":
            self._result(app)
        else:
            self._error(app.load_error or "未知资源错误")

    def _background(self) -> None:
        self.screen.fill(COLORS["background"])
        for x in range(0, WINDOW_SIZE[0], 64):
            pygame.draw.line(self.screen, (11, 20, 32), (x, 0), (x, WINDOW_SIZE[1]))
        for y in range(0, WINDOW_SIZE[1], 64):
            pygame.draw.line(self.screen, (11, 20, 32), (0, y), (WINDOW_SIZE[0], y))

    def _menu(self) -> None:
        self._diamond((640, 222), 82, COLORS["primary"], 4)
        self._diamond((640, 222), 52, COLORS["violet"], 2)
        pygame.draw.circle(self.screen, COLORS["text"], (640, 222), 10)
        self._center("ECHO // ZERO", 54, COLORS["text"], (640, 344), True)
        self._center("CALIBRATION CHAMBER", 18, COLORS["primary"], (640, 398), True)
        self._center("编排三拍 · 看见因果 · 改写结果", 22, COLORS["muted"], (640, 452))
        self._button(MENU_START_RECT, "开始校准  [ENTER]", True)
        self._center("三段短遭遇  /  一次协议构筑  /  一场双重锁定终检", 15, COLORS["muted"], (640, 674))

    def _battle(self, app: Any) -> None:
        run = app.level_run
        encounter = run.encounter
        definition = run.current_definition
        current, total = run.progress
        self._text_at("ECHO // ZERO", 22, COLORS["text"], (48, 28), True)
        self._text_at(f"LEVEL 01  {run.definition.display_name}", 14, COLORS["primary"], (48, 61), True)
        self._progress(current, total)
        self._text_at(definition.title, 26, COLORS["text"], (48, 105), True)
        self._text_at(definition.objective, 16, COLORS["muted"], (48, 139))
        self._draw_board(app)
        self._draw_hud(app)
        self._draw_event_strip(app)

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
        for intent in state.enemy_intents:
            target = self.cell_rect(intent.target_pos).inflate(-6, -6)
            pygame.draw.rect(self.screen, COLORS["danger_dark"], target, border_radius=10)
            pygame.draw.rect(self.screen, COLORS["danger"], target, 3, border_radius=10)
            actor = state.entities.get(intent.actor_id)
            if actor is not None:
                pygame.draw.line(self.screen, COLORS["danger"], self.cell_rect(actor.pos).center, target.center, 2)
            self._center(f"#{intent.order}", 15, COLORS["text"], target.center, True)
        for event in app.preview.events:
            if event.tick <= 3 and event.to_pos is not None and event.kind in {"moved", "pulled", "pushed"}:
                center = self.cell_rect(event.to_pos).center
                pygame.draw.circle(self.screen, COLORS["primary"], center, 18, 2)
                self._center(str(event.tick), 13, COLORS["primary"], center, True)
        for entity in state.entities.values():
            self._entity(entity)
        active = app.active_event()
        if active is not None and active.to_pos is not None:
            pulse = 7 + (pygame.time.get_ticks() // 70) % 7
            pygame.draw.rect(self.screen, COLORS["warning"], self.cell_rect(active.to_pos).inflate(-pulse, -pulse), 3, border_radius=10)

    def _entity(self, entity: Any) -> None:
        rect = self.cell_rect(entity.pos).inflate(-14, -14)
        center = rect.center
        if entity.faction is Faction.PLAYER:
            self._diamond(center, 26, COLORS["primary"], 0)
            self._diamond(center, 17, COLORS["background"], 0)
            pygame.draw.circle(self.screen, COLORS["text"], center, 6)
        elif entity.enemy_kind == "charger":
            pygame.draw.polygon(self.screen, COLORS["danger"], [(center[0] + 25, center[1]), (center[0] - 22, center[1] - 23), (center[0] - 22, center[1] + 23)])
            pygame.draw.polygon(self.screen, COLORS["background"], [(center[0] + 8, center[1]), (center[0] - 10, center[1] - 9), (center[0] - 10, center[1] + 9)])
        elif entity.enemy_kind == "sniper":
            pygame.draw.circle(self.screen, COLORS["violet"], center, 25, 4)
            pygame.draw.circle(self.screen, COLORS["danger"], center, 8)
            pygame.draw.line(self.screen, COLORS["violet"], (center[0] - 30, center[1]), (center[0] + 30, center[1]), 2)
            pygame.draw.line(self.screen, COLORS["violet"], (center[0], center[1] - 30), (center[0], center[1] + 30), 2)
        else:
            points = [(center[0] + 25, center[1]), (center[0] + 12, center[1] + 22), (center[0] - 12, center[1] + 22), (center[0] - 25, center[1]), (center[0] - 12, center[1] - 22), (center[0] + 12, center[1] - 22)]
            pygame.draw.polygon(self.screen, COLORS["warning"], points, 4)
        bar = pygame.Rect(rect.x, rect.bottom + 5, rect.width, 5)
        pygame.draw.rect(self.screen, COLORS["danger_dark"], bar)
        fill = bar.copy()
        fill.width = max(0, round(bar.width * entity.hp / entity.max_hp))
        pygame.draw.rect(self.screen, COLORS["success"] if entity.faction is Faction.PLAYER else COLORS["danger"], fill)

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
        label = "当前没有可执行的锁定攻击" if not intents else "  ·  ".join(f"#{item.order} {item.actor_id} → ({item.target_pos.x},{item.target_pos.y}) / {item.damage}伤害" for item in intents)
        self._text_at(label, 14, COLORS["text"], (intent_rect.x + 16, intent_rect.y + 42))
        self._text_at("三拍命令链  ·  两槽交换  ·  WASD移动 / E牵引 / Q护盾", 14, COLORS["text"], (PANEL_X, 266), True)
        for index, (command, rect) in enumerate(zip(encounter.commands, SLOT_RECTS, strict=True)):
            selected = app.ui.selected_slot == index
            self._panel(rect, COLORS["primary"] if selected else COLORS["border"], selected)
            badge = pygame.Rect(rect.x + 10, rect.y + 10, 44, 44)
            pygame.draw.rect(self.screen, COLORS["primary_dark"], badge, border_radius=8)
            self._center(str(index + 1), 18, COLORS["primary"], badge.center, True)
            self._text_at(app.command_label(command), 17, COLORS["text"], (rect.x + 70, rect.y + 8), True)
            self._text_at(app.preview_label(index + 1), 13, COLORS["muted"], (rect.x + 70, rect.y + 36))
        self._button(EXECUTE_RECT, "确认执行  [ENTER]", True)
        self._button(RESTART_RECT, "重启关卡  [R]", False)
        preview = app.preview.state
        preview_player = preview.entities.get("player")
        enemy_count = sum(entity.faction is Faction.ENEMY for entity in preview.entities.values())
        prediction = f"预演终态  CORE {preview_player.hp if preview_player else 0}  /  威胁 {enemy_count}"
        self._text_at(prediction, 15, COLORS["success"] if preview_player else COLORS["danger"], (PANEL_X, 638), True)
        self._text_at(run.current_definition.hint, 14, COLORS["warning"], (PANEL_X, 670))
        self._text_at(app.ui.feedback, 13, COLORS["muted"], (PANEL_X, 702))
        self._text_at("F3 调试" + ("：开" if app.ui.debug else "：关"), 12, COLORS["muted"], (1150, 756))
        if app.ui.debug:
            self._text_at(f"seed={run.run_seed}  turn={encounter.state.turn}  events={len(app.events)}  preview={'PASS' if app.ui.verification_ok is not False else 'FAIL'}", 12, COLORS["muted"], (PANEL_X, 756))

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
            self._panel(rect, COLORS["primary"] if index == app.ui.reward_focus else COLORS["border"], index == app.ui.reward_focus)
            self._center(f"0{index + 1}", 14, COLORS["primary"], (rect.centerx, rect.y + 32), True)
            self._protocol_icon(plugin.plugin_id, (rect.centerx, rect.y + 92))
            self._center(plugin.display_name, 24, COLORS["text"], (rect.centerx, rect.y + 154), True)
            self._center(" · ".join(plugin.tags), 13, COLORS["violet"], (rect.centerx, rect.y + 180), True)
            self._wrapped(plugin.description, 15, COLORS["muted"], pygame.Rect(rect.x + 30, rect.y + 202, rect.width - 60, 78), 24)
            self._center(f"按 {index + 1} 安装", 15, COLORS["primary"], (rect.centerx, rect.bottom - 32), True)
        self._center("选择后立即进入下一次校准", 14, COLORS["muted"], (640, 618))

    def _result(self, app: Any) -> None:
        clear = app.level_run.phase is LevelPhase.LEVEL_CLEAR
        color = COLORS["success"] if clear else COLORS["danger"]
        self._diamond((640, 206), 70, color, 4)
        self._center("LEVEL CLEAR" if clear else "CALIBRATION FAILED", 46, COLORS["text"], (640, 340), True)
        subtitle = "校准舱已稳定，协议链路保持在线。" if clear else "核心离线。重启关卡后可重新编排因果。"
        self._center(subtitle, 18, COLORS["muted"], (640, 400))
        plugins = " / ".join(
            definition.display_name + (f"×{stacks}" if stacks > 1 else "")
            for definition, stacks in app.level_run.build_summary
        ) or "无"
        self._center(f"完成遭遇 {len(app.level_run.completed_encounters)}/3   ·   Build {plugins}", 16, color, (640, 456), True)
        self._button(RESULT_RESTART_RECT, "重新开始 Level 1  [ENTER / R]", True)
        self._center("ESC 退出", 13, COLORS["muted"], (640, 686))

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
        return self._font(size, bold).render(text, True, color)

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
