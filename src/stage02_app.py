"""Stage02 最小完整战斗界面：输入/展示，不拥有结算规则。"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from src.domain import Command, CommandType, Direction, Encounter, EncounterOutcome, Faction, GridPos, LogicEvent, state_fingerprint
from src.stage02_scenario import create_stage02_state, opening_commands

WINDOW_SIZE = (1200, 760)
CELL_SIZE = 72
GRID_ORIGIN = (40, 116)
PANEL_X = 656
SLOT_RECTS = tuple(pygame.Rect(PANEL_X, 250 + index * 82, 504, 66) for index in range(3))
EXECUTE_RECT = pygame.Rect(PANEL_X, 514, 312, 58)
RESET_RECT = pygame.Rect(986, 514, 174, 58)

COLORS = {
    "background": (9, 13, 22), "surface": (24, 32, 46), "border": (62, 80, 108),
    "text": (241, 245, 249), "muted": (148, 163, 184), "primary": (56, 189, 248),
    "danger": (251, 113, 133), "success": (74, 222, 128), "warning": (250, 204, 21),
    "player": (96, 165, 250), "enemy": (248, 113, 113), "grid_a": (19, 28, 42),
    "grid_b": (24, 35, 52), "wall": (71, 85, 105), "intent": (127, 29, 29),
}

EVENT_LABELS = {
    "enemy_moved": "敌人 BFS 移动", "intent_locked": "敌人锁定意图", "moved": "移动",
    "pushed": "推动", "pulled": "牵引", "damaged": "伤害", "died": "单位死亡",
    "shielded": "获得护盾", "shield_absorbed": "护盾吸收", "attack_missed": "锁定攻击落空",
    "intent_cancelled": "死亡取消意图", "push_missed": "推击落空", "pull_missed": "牵引失败",
    "move_blocked": "移动受阻", "push_blocked": "推动受阻", "waited": "待机",
}


@dataclass
class UiState:
    selected_slot: int | None = None
    debug: bool = False
    verification_ok: bool | None = None
    feedback: str = "交换三拍，或选槽后点击战场目标。"


class Stage02App:
    def __init__(self, smoke_test: bool = False) -> None:
        self.smoke_test = smoke_test
        self.screen: pygame.Surface | None = None
        self.fonts: dict[tuple[int, bool], pygame.font.Font] = {}
        self.ui = UiState()
        self.events: tuple[LogicEvent, ...] = ()
        self.animation_started_ms = 0
        self._restart()

    def run(self) -> int:
        pygame.init()
        try:
            self.screen = pygame.display.set_mode(WINDOW_SIZE)
            pygame.display.set_caption("EchoZero | Stage02 核心战斗闭环")
            if self.smoke_test:
                self._run_flow_smoke()
            clock = pygame.time.Clock()
            running = True
            frames = 0
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        running = self._handle_key(event.key)
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        self._handle_click(event.pos, event.button)
                self._draw()
                pygame.display.flip()
                frames += 1
                if self.smoke_test and frames >= 2:
                    running = False
                clock.tick(60)
            return 0
        finally:
            pygame.quit()

    @property
    def preview(self):
        return self.encounter.preview()

    def _restart(self) -> None:
        self.encounter = Encounter(create_stage02_state())
        for command in opening_commands():
            self.encounter.set_command(command)
        self.events = self.encounter.preparation_events
        self.animation_started_ms = pygame.time.get_ticks()
        self.ui = UiState(feedback="开局提示：同样三条命令，先后顺序决定能否击杀并取消意图。")

    def _handle_key(self, key: int) -> bool:
        if key == pygame.K_ESCAPE:
            return False
        if key in (pygame.K_1, pygame.K_2, pygame.K_3):
            self._choose_slot(key - pygame.K_1)
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            self._execute()
        elif key == pygame.K_r:
            self._restart()
        elif key == pygame.K_F3:
            self.ui.debug = not self.ui.debug
        elif key in (pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d) and self.ui.selected_slot is not None:
            directions = {pygame.K_w: Direction.UP, pygame.K_d: Direction.RIGHT, pygame.K_s: Direction.DOWN, pygame.K_a: Direction.LEFT}
            self._assign(CommandType.MOVE, direction=directions[key])
        elif key == pygame.K_q and self.ui.selected_slot is not None:
            self._assign(CommandType.SHIELD)
        return True

    def _run_flow_smoke(self) -> None:
        """走通真实 App/Encounter 接口的胜利与重开路径。"""
        self._choose_slot(2)
        self._choose_slot(0)
        self._choose_slot(0)
        self._choose_slot(2)
        self._choose_slot(1)
        self._execute()
        scripted_turns = [
            [Command("player", CommandType.MOVE, 1, Direction.RIGHT), Command("player", CommandType.MOVE, 2, Direction.RIGHT)],
            [Command("player", CommandType.MOVE, 1, Direction.UP), Command("player", CommandType.MOVE, 2, Direction.RIGHT), Command("player", CommandType.MOVE, 3, Direction.RIGHT)],
            [Command("player", CommandType.PUSH, 1, Direction.RIGHT), Command("player", CommandType.PULL, 2, target_entity_id="sniper"), Command("player", CommandType.PUSH, 3, Direction.RIGHT)],
        ]
        for commands in scripted_turns:
            for command in commands:
                self.encounter.set_command(command)
            self._execute()
        if self.encounter.outcome is not EncounterOutcome.VICTORY:
            raise RuntimeError("Stage02 flow smoke did not reach victory")
        self._restart()
        if self.encounter.outcome is not EncounterOutcome.ONGOING:
            raise RuntimeError("Stage02 flow smoke restart failed")

    def _handle_click(self, pos: tuple[int, int], button: int) -> None:
        for index, rect in enumerate(SLOT_RECTS):
            if rect.collidepoint(pos):
                if button == 3 and self.encounter.outcome is EncounterOutcome.ONGOING:
                    self.encounter.set_command(Command("player", CommandType.WAIT, index + 1))
                else:
                    self._choose_slot(index)
                return
        if EXECUTE_RECT.collidepoint(pos):
            self._execute()
        elif RESET_RECT.collidepoint(pos):
            self._restart()
        elif button == 1 and self.ui.selected_slot is not None:
            cell = GridPos((pos[0] - GRID_ORIGIN[0]) // CELL_SIZE, (pos[1] - GRID_ORIGIN[1]) // CELL_SIZE)
            if self.encounter.state.in_bounds(cell):
                self._assign_from_cell(cell)

    def _choose_slot(self, index: int) -> None:
        if self.encounter.outcome is not EncounterOutcome.ONGOING:
            return
        if self.ui.selected_slot is None:
            self.ui.selected_slot = index
        elif self.ui.selected_slot == index:
            self.ui.selected_slot = None
        else:
            self.encounter.swap_slots(self.ui.selected_slot, index)
            self.ui.selected_slot = index

    def _assign_from_cell(self, cell: GridPos) -> None:
        player = self.encounter.state.entities.get("player")
        if player is None:
            return
        target = self.encounter.state.entity_at(cell)
        delta = (cell.x - player.pos.x, cell.y - player.pos.y)
        direction = next((item for item in Direction if item.delta == delta), None)
        if cell == player.pos:
            self._assign(CommandType.SHIELD)
        elif target is not None and target.faction is Faction.ENEMY:
            if direction is not None:
                self._assign(CommandType.PUSH, direction=direction)
            elif (cell.x == player.pos.x or cell.y == player.pos.y) and player.pos.manhattan_distance(cell) <= 2:
                self._assign(CommandType.PULL, target_id=target.entity_id)
            else:
                self.ui.feedback = "牵引目标必须在同一直线 2 格内。"
        elif direction is not None:
            self._assign(CommandType.MOVE, direction=direction)
        else:
            self.ui.feedback = "移动/推击只选相邻格；牵引可选直线 2 格敌人。"

    def _assign(self, command_type: CommandType, direction: Direction | None = None, target_id: str | None = None) -> None:
        assert self.ui.selected_slot is not None
        slot = self.ui.selected_slot + 1
        self.encounter.set_command(Command("player", command_type, slot, direction, target_id))
        self.ui.feedback = f"第 {slot} 拍已设为 {self._command_label(self.encounter.commands[slot - 1])}。"

    def _execute(self) -> None:
        if self.encounter.outcome is not EncounterOutcome.ONGOING:
            return
        expected = state_fingerprint(self.preview.state)
        resolution = self.encounter.confirm_turn()
        self.ui.verification_ok = state_fingerprint(resolution.result.state) == expected
        self.events = resolution.result.events + resolution.preparation_events
        self.animation_started_ms = pygame.time.get_ticks()
        self.ui.selected_slot = None
        self.ui.feedback = "回合完成：敌人已移动并公开下一轮锁定意图。"

    def _draw(self) -> None:
        assert self.screen is not None
        self.screen.fill(COLORS["background"])
        self.screen.blit(self._text("EchoZero / Stage02 测试 Encounter", 27, COLORS["text"], True), (40, 28))
        self.screen.blit(self._text("编排 → 因果预演 → 执行 → 敌人 BFS 响应 → 胜负", 17, COLORS["muted"]), (40, 68))
        self._draw_board()
        self._draw_panel()
        self._draw_events()

    def _draw_board(self) -> None:
        assert self.screen is not None
        state = self.encounter.state
        for y in range(state.height):
            for x in range(state.width):
                rect = self._cell_rect(GridPos(x, y))
                pygame.draw.rect(self.screen, COLORS["grid_a"] if (x + y) % 2 == 0 else COLORS["grid_b"], rect)
                pygame.draw.rect(self.screen, COLORS["border"], rect, 1)
        for wall in state.walls:
            pygame.draw.rect(self.screen, COLORS["wall"], self._cell_rect(wall).inflate(-10, -10), border_radius=5)
        for intent in state.enemy_intents:
            rect = self._cell_rect(intent.target_pos).inflate(-7, -7)
            pygame.draw.rect(self.screen, COLORS["intent"], rect, border_radius=8)
            pygame.draw.rect(self.screen, COLORS["danger"], rect, 3, border_radius=8)
            self._center_text(str(intent.order), 17, COLORS["text"], rect.center, True)
        for entity in state.entities.values():
            rect = self._cell_rect(entity.pos).inflate(-14, -14)
            color = COLORS["player"] if entity.faction is Faction.PLAYER else COLORS["enemy"]
            pygame.draw.rect(self.screen, color, rect, border_radius=9)
            label = "P" if entity.faction is Faction.PLAYER else ("C" if entity.enemy_kind == "charger" else "S")
            self._center_text(label, 20, COLORS["background"], (rect.centerx, rect.y + 18), True)
            self._center_text(f"{entity.hp}/{entity.max_hp}  ◇{entity.shield}", 12, COLORS["background"], (rect.centerx, rect.bottom - 12), True)
        for event in self.preview.events:
            if event.tick <= 3 and event.to_pos is not None and event.kind in {"moved", "pulled", "pushed"}:
                pygame.draw.circle(self.screen, COLORS["primary"], self._cell_rect(event.to_pos).center, 13, 2)
                self._center_text(str(event.tick), 13, COLORS["primary"], self._cell_rect(event.to_pos).center, True)
        active_event = self._active_animation_event()
        if active_event is not None and active_event.to_pos is not None:
            pulse = 4 + (pygame.time.get_ticks() // 80) % 4
            pygame.draw.rect(self.screen, COLORS["warning"], self._cell_rect(active_event.to_pos).inflate(-pulse, -pulse), 3, border_radius=9)

    def _draw_panel(self) -> None:
        assert self.screen is not None
        outcome = self.encounter.outcome
        title = {EncounterOutcome.ONGOING: f"回合 {self.encounter.state.turn}", EncounterOutcome.VICTORY: "VICTORY", EncounterOutcome.DEFEAT: "DEFEAT"}[outcome]
        color = COLORS["success"] if outcome is EncounterOutcome.VICTORY else COLORS["danger"] if outcome is EncounterOutcome.DEFEAT else COLORS["primary"]
        self.screen.blit(self._text(title, 26, color, True), (PANEL_X, 112))
        intents = self.encounter.state.enemy_intents
        intent_text = "无锁定攻击" if not intents else "  /  ".join(f"#{i.order} {i.actor_id}→({i.target_pos.x},{i.target_pos.y}) {i.damage}伤害" for i in intents)
        self.screen.blit(self._text(intent_text, 15, COLORS["text"]), (PANEL_X, 154))
        self.screen.blit(self._text("选槽后：点相邻空格=移动；点敌人=推击/牵引；点自己=护盾", 14, COLORS["muted"]), (PANEL_X, 190))
        self.screen.blit(self._text("也可 WASD 移动、Q 护盾、右键槽位待机", 14, COLORS["muted"]), (PANEL_X, 214))
        for index, (command, rect) in enumerate(zip(self.encounter.commands, SLOT_RECTS, strict=True)):
            pygame.draw.rect(self.screen, COLORS["surface"], rect, border_radius=8)
            pygame.draw.rect(self.screen, COLORS["text"] if self.ui.selected_slot == index else COLORS["border"], rect, 3 if self.ui.selected_slot == index else 1, border_radius=8)
            self._center_text(str(index + 1), 20, COLORS["primary"], (rect.x + 28, rect.centery), True)
            self.screen.blit(self._text(self._command_label(command), 18, COLORS["text"], True), (rect.x + 58, rect.y + 11))
            self.screen.blit(self._text(self._preview_label(index + 1), 13, COLORS["muted"]), (rect.x + 58, rect.y + 38))
        pygame.draw.rect(self.screen, COLORS["primary"] if outcome is EncounterOutcome.ONGOING else COLORS["border"], EXECUTE_RECT, border_radius=8)
        self._center_text("确认执行 [Enter]" if outcome is EncounterOutcome.ONGOING else "战斗已结束", 19, COLORS["text"], EXECUTE_RECT.center, True)
        pygame.draw.rect(self.screen, COLORS["surface"], RESET_RECT, border_radius=8)
        pygame.draw.rect(self.screen, COLORS["border"], RESET_RECT, 2, border_radius=8)
        self._center_text("重新开始 [R]", 17, COLORS["text"], RESET_RECT.center, True)
        self.screen.blit(self._text(self.ui.feedback, 14, COLORS["warning"]), (PANEL_X, 592))
        if self.ui.verification_ok is not None:
            label = "同源校验 PASS" if self.ui.verification_ok else "同源校验 FAIL"
            self.screen.blit(self._text(label, 14, COLORS["success"] if self.ui.verification_ok else COLORS["danger"], True), (PANEL_X, 620))
        if self.ui.debug:
            self.screen.blit(self._text(f"DEBUG  entities={len(self.encounter.state.entities)} events={len(self.events)}", 13, COLORS["muted"]), (PANEL_X, 646))

    def _draw_events(self) -> None:
        assert self.screen is not None
        self.screen.blit(self._text("逻辑事件反馈（F3 调试信息）", 17, COLORS["text"], True), (40, 574))
        lines = [f"t{event.tick} {EVENT_LABELS.get(event.kind, event.kind)}" for event in self.events if event.kind != "waited"][-5:]
        active = self._active_animation_event()
        active_label = EVENT_LABELS.get(active.kind, active.kind) if active is not None else ""
        for index, line in enumerate(lines):
            color = COLORS["warning"] if active_label and active_label in line else COLORS["muted"]
            self.screen.blit(self._text(line, 14, color), (40, 608 + index * 24))

    def _active_animation_event(self) -> LogicEvent | None:
        visible = [event for event in self.events if event.kind != "waited"]
        if not visible:
            return None
        elapsed = pygame.time.get_ticks() - self.animation_started_ms
        index = elapsed // 260
        return visible[index] if 0 <= index < len(visible) else None

    def _preview_label(self, slot: int) -> str:
        events = [event for event in self.preview.events if event.tick == slot]
        return " / ".join(EVENT_LABELS.get(event.kind, event.kind) for event in events) or "无事件"

    @staticmethod
    def _command_label(command: Command) -> str:
        if command.command_type in {CommandType.MOVE, CommandType.PUSH}:
            return f"{command.command_type.value.upper()} {command.direction.name if command.direction else '?'}"
        if command.command_type is CommandType.PULL:
            return f"PULL {command.target_entity_id}"
        return command.command_type.value.upper()

    def _font(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in self.fonts:
            name = pygame.font.match_font("microsoftyahei,simhei,arial")
            self.fonts[key] = pygame.font.Font(name, size)
            self.fonts[key].bold = bold
        return self.fonts[key]

    def _text(self, text: str, size: int, color: tuple[int, int, int], bold: bool = False) -> pygame.Surface:
        return self._font(size, bold).render(text, True, color)

    @staticmethod
    def _cell_rect(pos: GridPos) -> pygame.Rect:
        return pygame.Rect(GRID_ORIGIN[0] + pos.x * CELL_SIZE, GRID_ORIGIN[1] + pos.y * CELL_SIZE, CELL_SIZE, CELL_SIZE)

    def _center_text(self, text: str, size: int, color: tuple[int, int, int], center: tuple[int, int], bold: bool = False) -> None:
        assert self.screen is not None
        surface = self._text(text, size, color, bold)
        self.screen.blit(surface, surface.get_rect(center=center))
