"""Stage 01 pygame 灰盒：只消费领域状态和逻辑事件。"""

from __future__ import annotations

import os
from dataclasses import dataclass

import pygame

from src.demo_scenario import create_demo_state, default_commands
from src.domain import Command, CommandType, Faction, GridPos, execute_turn, preview_turn, state_fingerprint

WINDOW_SIZE = (1200, 760)
CELL_SIZE = 72
GRID_ORIGIN = (40, 112)
PANEL_X = 656
SLOT_RECTS = tuple(pygame.Rect(PANEL_X, 236 + index * 88, 504, 72) for index in range(3))
EXECUTE_RECT = pygame.Rect(PANEL_X, 520, 320, 64)
RESET_RECT = pygame.Rect(992, 520, 168, 64)

COLORS = {
    "background": (11, 11, 16),
    "surface": (30, 30, 35),
    "surface_high": (35, 35, 40),
    "border": (51, 65, 85),
    "text": (248, 250, 252),
    "muted": (160, 174, 194),
    "primary": (59, 130, 246),
    "focus": (248, 250, 252),
    "danger": (248, 113, 113),
    "danger_dark": (89, 24, 31),
    "success": (74, 222, 128),
    "success_dark": (20, 83, 45),
    "player": (96, 165, 250),
    "enemy": (248, 113, 113),
    "grid_a": (23, 30, 42),
    "grid_b": (28, 37, 51),
    "wall": (71, 85, 105),
}

COMMAND_LABELS = {
    CommandType.WAIT: ("待机", "不执行动作"),
    CommandType.MOVE: ("移动 ↓", "向下移动 1 格"),
    CommandType.PUSH: ("推击 →", "命中相邻单位，伤害 1"),
    CommandType.PULL: ("牵引", "直线 2 格内拉近敌人"),
}

EVENT_LABELS = {
    "push_missed": "推击落空",
    "pull_missed": "牵引失败",
    "pulled": "敌人被牵引",
    "moved": "玩家移动",
    "damaged": "造成伤害",
    "died": "单位死亡",
    "intent_cancelled": "敌人意图取消",
    "attack_missed": "敌人攻击落空",
    "command_cancelled": "命令取消",
    "push_blocked": "推击受阻",
    "move_blocked": "移动受阻",
    "pull_blocked": "牵引受阻",
    "pushed": "敌人被推动",
    "waited": "待机",
}


@dataclass
class UiState:
    selected_slot: int | None = None
    executed: bool = False
    verification_ok: bool | None = None


class GrayboxApp:
    def __init__(self, smoke_test: bool = False) -> None:
        self.smoke_test = smoke_test
        self.state = create_demo_state()
        self.commands = default_commands()
        self.ui = UiState()
        self.preview = preview_turn(self.state, self.commands)
        self.fonts: dict[tuple[int, bool], pygame.font.Font] = {}
        self.screen: pygame.Surface | None = None

    def run(self) -> int:
        pygame.init()
        try:
            self.screen = pygame.display.set_mode(WINDOW_SIZE)
            pygame.display.set_caption("EchoZero | Stage 01 确定性灰盒")
            clock = pygame.time.Clock()
            running = True
            frame_count = 0
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        running = self._handle_key(event.key)
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        self._handle_click(event.pos)
                self._draw()
                pygame.display.flip()
                frame_count += 1
                if self.smoke_test and frame_count >= 1:
                    running = False
                clock.tick(60)
            return 0
        finally:
            pygame.quit()

    def _handle_key(self, key: int) -> bool:
        if key == pygame.K_ESCAPE:
            return False
        if key in (pygame.K_1, pygame.K_2, pygame.K_3):
            self._choose_slot(key - pygame.K_1)
        elif key in (pygame.K_LEFT, pygame.K_UP) and self.ui.selected_slot is not None:
            self._swap(self.ui.selected_slot, max(0, self.ui.selected_slot - 1))
        elif key in (pygame.K_RIGHT, pygame.K_DOWN) and self.ui.selected_slot is not None:
            self._swap(self.ui.selected_slot, min(2, self.ui.selected_slot + 1))
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            self._execute()
        elif key == pygame.K_r:
            self._reset()
        return True

    def _handle_click(self, pos: tuple[int, int]) -> None:
        for index, rect in enumerate(SLOT_RECTS):
            if rect.collidepoint(pos):
                self._choose_slot(index)
                return
        if EXECUTE_RECT.collidepoint(pos):
            self._execute()
        elif RESET_RECT.collidepoint(pos):
            self._reset()

    def _choose_slot(self, index: int) -> None:
        if self.ui.executed:
            return
        if self.ui.selected_slot is None:
            self.ui.selected_slot = index
        elif self.ui.selected_slot == index:
            self.ui.selected_slot = None
        else:
            self._swap(self.ui.selected_slot, index)

    def _swap(self, first: int, second: int) -> None:
        if self.ui.executed or first == second:
            return
        self.commands[first], self.commands[second] = self.commands[second], self.commands[first]
        self.commands = [command.in_slot(index + 1) for index, command in enumerate(self.commands)]
        self.ui.selected_slot = second
        self.preview = preview_turn(self.state, self.commands)

    def _execute(self) -> None:
        if self.ui.executed:
            return
        expected_hash = state_fingerprint(self.preview.state)
        result = execute_turn(self.state, self.commands)
        self.ui.verification_ok = state_fingerprint(result.state) == expected_hash
        self.state = result.state
        self.preview = result
        self.ui.executed = True
        self.ui.selected_slot = None

    def _reset(self) -> None:
        self.state = create_demo_state()
        self.commands = default_commands()
        self.preview = preview_turn(self.state, self.commands)
        self.ui = UiState()

    def _font(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in self.fonts:
            font_name = pygame.font.match_font("microsoftyahei,simhei,arial")
            self.fonts[key] = pygame.font.Font(font_name, size)
            self.fonts[key].bold = bold
        return self.fonts[key]

    def _text(self, text: str, size: int, color: tuple[int, int, int], bold: bool = False) -> pygame.Surface:
        return self._font(size, bold).render(text, True, color)

    def _draw(self) -> None:
        assert self.screen is not None
        self.screen.fill(COLORS["background"])
        self.screen.blit(self._text("EchoZero / 确定性因果灰盒", 28, COLORS["text"], True), (40, 28))
        self.screen.blit(self._text("同样三条命令，只换顺序，结局就会改变。", 18, COLORS["muted"]), (40, 68))
        self._draw_board()
        self._draw_intent()
        self._draw_timeline()
        self._draw_actions()
        self._draw_event_log()

    def _draw_board(self) -> None:
        assert self.screen is not None
        for y in range(6):
            for x in range(8):
                rect = self._cell_rect(GridPos(x, y))
                color = COLORS["grid_a"] if (x + y) % 2 == 0 else COLORS["grid_b"]
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, COLORS["border"], rect, 1)
        for wall in self.state.walls:
            pygame.draw.rect(self.screen, COLORS["wall"], self._cell_rect(wall).inflate(-12, -12), border_radius=4)

        intent = self.state.enemy_intents[0]
        target_rect = self._cell_rect(intent.target_pos).inflate(-8, -8)
        pygame.draw.rect(self.screen, COLORS["danger_dark"], target_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLORS["danger"], target_rect, 3, border_radius=8)
        self._center_text("锁定", 16, COLORS["text"], target_rect.center)

        for event in self.preview.events:
            if event.tick <= 3 and event.to_pos is not None and event.kind in {"moved", "pulled", "pushed"}:
                cell = self._cell_rect(event.to_pos)
                center = (cell.x + 17, cell.y + 17)
                pygame.draw.circle(self.screen, COLORS["primary"], center, 15)
                self._center_text(str(event.tick), 16, COLORS["text"], center, True)

        for entity in self.state.entities.values():
            rect = self._cell_rect(entity.pos).inflate(-16, -16)
            color = COLORS["player"] if entity.faction is Faction.PLAYER else COLORS["enemy"]
            pygame.draw.rect(self.screen, color, rect, border_radius=10)
            label = "P" if entity.faction is Faction.PLAYER else "E1"
            self._center_text(label, 19, COLORS["background"], (rect.centerx, rect.y + 20), True)
            hp = self._text(f"HP {entity.hp}/{entity.max_hp}", 12, COLORS["background"], True)
            self.screen.blit(hp, (rect.centerx - hp.get_width() // 2, rect.bottom - 19))

        if not self.ui.executed:
            preview_player = self.preview.state.entities.get("player")
            if preview_player is not None:
                ghost = self._cell_rect(preview_player.pos).inflate(-16, -16)
                pygame.draw.rect(self.screen, COLORS["success"] if "sniper" not in self.preview.state.entities else COLORS["danger"], ghost, 3, border_radius=8)

        outcome = self._outcome()
        badge_color = COLORS["success_dark"] if outcome[0] else COLORS["danger_dark"]
        badge_border = COLORS["success"] if outcome[0] else COLORS["danger"]
        badge = pygame.Rect(40, 560, 576, 56)
        pygame.draw.rect(self.screen, badge_color, badge, border_radius=8)
        pygame.draw.rect(self.screen, badge_border, badge, 2, border_radius=8)
        self.screen.blit(self._text(outcome[1], 20, COLORS["text"], True), (56, 576))

    def _draw_intent(self) -> None:
        assert self.screen is not None
        rect = pygame.Rect(PANEL_X, 112, 504, 96)
        pygame.draw.rect(self.screen, COLORS["surface"], rect, border_radius=8)
        pygame.draw.rect(self.screen, COLORS["danger"], rect, 2, border_radius=8)
        self.screen.blit(self._text("敌人意图 #1 / 已锁定", 18, COLORS["danger"], True), (PANEL_X + 16, 126))
        self.screen.blit(self._text("校验射手将攻击“锁定”格，造成 2 伤害", 17, COLORS["text"]), (PANEL_X + 16, 164))

    def _draw_timeline(self) -> None:
        assert self.screen is not None
        self.screen.blit(self._text("三拍命令链 / 点击两个槽位交换", 18, COLORS["text"], True), (PANEL_X, 214))
        for index, (command, rect) in enumerate(zip(self.commands, SLOT_RECTS, strict=True)):
            selected = self.ui.selected_slot == index
            fill = COLORS["surface_high"] if selected else COLORS["surface"]
            border = COLORS["focus"] if selected else COLORS["border"]
            pygame.draw.rect(self.screen, fill, rect, border_radius=8)
            pygame.draw.rect(self.screen, border, rect, 3 if selected else 1, border_radius=8)
            number_rect = pygame.Rect(rect.x + 12, rect.y + 12, 48, 48)
            pygame.draw.rect(self.screen, COLORS["primary"], number_rect, border_radius=6)
            self._center_text(str(index + 1), 22, COLORS["background"], number_rect.center, True)
            title, detail = COMMAND_LABELS[command.command_type]
            self.screen.blit(self._text(title, 19, COLORS["text"], True), (rect.x + 76, rect.y + 10))
            self.screen.blit(self._text(detail, 15, COLORS["muted"]), (rect.x + 76, rect.y + 39))
            if selected:
                self.screen.blit(self._text("已选中", 14, COLORS["text"], True), (rect.right - 76, rect.y + 26))

    def _draw_actions(self) -> None:
        assert self.screen is not None
        execute_fill = COLORS["border"] if self.ui.executed else COLORS["primary"]
        pygame.draw.rect(self.screen, execute_fill, EXECUTE_RECT, border_radius=8)
        execute_label = "已执行 / 按 R 重置" if self.ui.executed else "确认执行  [Enter]"
        self._center_text(execute_label, 20, COLORS["text"], EXECUTE_RECT.center, True)
        pygame.draw.rect(self.screen, COLORS["surface"], RESET_RECT, border_radius=8)
        pygame.draw.rect(self.screen, COLORS["border"], RESET_RECT, 2, border_radius=8)
        self._center_text("重置  [R]", 18, COLORS["text"], RESET_RECT.center, True)
        self.screen.blit(self._text("键盘：1/2/3 选槽  ·  方向键换序  ·  Esc 退出", 14, COLORS["muted"]), (PANEL_X, 596))

    def _draw_event_log(self) -> None:
        assert self.screen is not None
        self.screen.blit(self._text("因果预演", 18, COLORS["text"], True), (40, 640))
        visible = [event for event in self.preview.events if event.kind != "waited"][-5:]
        x = 40
        for event in visible:
            label = f"{event.tick}. {EVENT_LABELS.get(event.kind, event.kind)}"
            color = COLORS["danger"] if event.kind in {"damaged", "died", "push_missed", "pull_missed"} else COLORS["muted"]
            surface = self._text(label, 15, color, event.kind in {"died", "intent_cancelled"})
            self.screen.blit(surface, (x, 680))
            x += surface.get_width() + 24
        if self.ui.verification_ok is not None:
            verify = "校验通过：预演终态 = 执行终态" if self.ui.verification_ok else "校验失败：终态不一致"
            color = COLORS["success"] if self.ui.verification_ok else COLORS["danger"]
            self.screen.blit(self._text(verify, 16, color, True), (656, 648))

    def _outcome(self) -> tuple[bool, str]:
        player = self.preview.state.entities.get("player")
        enemy_dead = "sniper" not in self.preview.state.entities
        if enemy_dead:
            return True, "安全 / 敌人被击杀，锁定攻击已取消"
        if player is not None and player.hp < player.max_hp:
            return False, f"受伤 / 玩家会剩余 {player.hp} HP"
        return False, "未解决 / 敌人仍存活"

    @staticmethod
    def _cell_rect(pos: GridPos) -> pygame.Rect:
        return pygame.Rect(GRID_ORIGIN[0] + pos.x * CELL_SIZE, GRID_ORIGIN[1] + pos.y * CELL_SIZE, CELL_SIZE, CELL_SIZE)

    def _center_text(self, text: str, size: int, color: tuple[int, int, int], center: tuple[int, int], bold: bool = False) -> None:
        assert self.screen is not None
        surface = self._text(text, size, color, bold)
        self.screen.blit(surface, surface.get_rect(center=center))
