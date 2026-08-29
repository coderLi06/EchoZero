"""Stage03 formal entry flow: menu, Level 1, reward and result scenes."""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import pygame

from src.domain import (
    Command,
    CommandType,
    Direction,
    Faction,
    GridPos,
    LevelPhase,
    LevelRun,
    LogicEvent,
    state_fingerprint,
)
from src.infrastructure import ContentLoadError, load_level_one
from src.presentation.audio import CueAudio
from src.presentation.stage03_renderer import (
    CELL_SIZE,
    EXECUTE_RECT,
    GRID_ORIGIN,
    MENU_START_RECT,
    RESTART_RECT,
    RESULT_RESTART_RECT,
    REWARD_RECTS,
    SLOT_RECTS,
    WINDOW_SIZE,
    EVENT_LABELS,
    Stage03Renderer,
)


class AppScene(str, Enum):
    MENU = "menu"
    BATTLE = "battle"
    REWARD = "reward"
    RESULT = "result"
    ERROR = "error"


@dataclass
class Stage03UiState:
    selected_slot: int | None = None
    reward_focus: int = 0
    debug: bool = False
    verification_ok: bool | None = None
    feedback: str = "选择命令槽，再点击战场目标。"


class Stage03App:
    def __init__(
        self,
        smoke_test: bool = False,
        data_root: Path | None = None,
        seed: int | None = None,
        random_rewards: bool = False,
        rng: random.Random | None = None,
    ) -> None:
        self.smoke_test = smoke_test
        self.screen: pygame.Surface | None = None
        self.renderer: Stage03Renderer | None = None
        self.audio = CueAudio()
        self.scene = AppScene.MENU
        self.ui = Stage03UiState()
        self.events: tuple[LogicEvent, ...] = ()
        self.animation_started_ms = 0
        self.load_error: str | None = None
        self._fixed_seed = seed
        self._random_rewards = random_rewards
        self._seed_source = rng or random.Random()
        try:
            level, plugins = load_level_one(data_root)
            initial_seed = seed if seed is not None else level.seed
            self.level_run = LevelRun(level, plugins, initial_seed)
        except ContentLoadError as exc:
            self.load_error = str(exc)
            self.scene = AppScene.ERROR

    def run(self) -> int:
        pygame.init()
        try:
            self.screen = pygame.display.set_mode(WINDOW_SIZE)
            pygame.display.set_caption("EchoZero | Level 1 · 校准舱")
            self.renderer = Stage03Renderer(self.screen)
            self.audio.initialise()
            if self.smoke_test and self.load_error is None:
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
                self.renderer.draw(self)
                pygame.display.flip()
                frames += 1
                if self.smoke_test and frames >= 2:
                    running = False
                clock.tick(60)
            return 2 if self.load_error is not None else 0
        finally:
            pygame.quit()

    @property
    def preview(self):
        return self.level_run.encounter.preview()

    def _handle_key(self, key: int) -> bool:
        if key == pygame.K_ESCAPE:
            return False
        if self.scene is AppScene.MENU:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self._start_level()
            return True
        if self.scene is AppScene.RESULT:
            if key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r):
                self._start_level()
            return True
        if self.scene is AppScene.REWARD:
            if key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self._choose_reward(key - pygame.K_1)
            elif key in (pygame.K_LEFT, pygame.K_a):
                self.ui.reward_focus = (self.ui.reward_focus - 1) % len(self.level_run.reward_choices)
            elif key in (pygame.K_RIGHT, pygame.K_d):
                self.ui.reward_focus = (self.ui.reward_focus + 1) % len(self.level_run.reward_choices)
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self._choose_reward(self.ui.reward_focus)
            elif key == pygame.K_r:
                self._start_level()
            return True
        if self.scene is not AppScene.BATTLE:
            return True
        if key in (pygame.K_1, pygame.K_2, pygame.K_3):
            self._choose_slot(key - pygame.K_1)
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            self._execute()
        elif key == pygame.K_r:
            self._start_level()
        elif key == pygame.K_F3:
            self.ui.debug = not self.ui.debug
        elif key in (pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d) and self.ui.selected_slot is not None:
            direction = {
                pygame.K_w: Direction.UP,
                pygame.K_d: Direction.RIGHT,
                pygame.K_s: Direction.DOWN,
                pygame.K_a: Direction.LEFT,
            }[key]
            self._assign(CommandType.MOVE, direction=direction)
        elif key == pygame.K_q and self.ui.selected_slot is not None:
            self._assign(CommandType.SHIELD)
        elif key == pygame.K_e and self.ui.selected_slot is not None:
            self._assign_nearest_pull()
        return True

    def _handle_click(self, pos: tuple[int, int], button: int) -> None:
        if button != 1 and not (self.scene is AppScene.BATTLE and button == 3):
            return
        if self.scene is AppScene.MENU and MENU_START_RECT.collidepoint(pos):
            self._start_level()
        elif self.scene is AppScene.RESULT and RESULT_RESTART_RECT.collidepoint(pos):
            self._start_level()
        elif self.scene is AppScene.REWARD:
            for index, rect in enumerate(REWARD_RECTS[: len(self.level_run.reward_choices)]):
                if rect.collidepoint(pos):
                    self._choose_reward(index)
                    return
        elif self.scene is AppScene.BATTLE:
            self._handle_battle_click(pos, button)

    def _handle_battle_click(self, pos: tuple[int, int], button: int) -> None:
        encounter = self.level_run.encounter
        for index, rect in enumerate(SLOT_RECTS):
            if rect.collidepoint(pos):
                if button == 3:
                    encounter.set_command(Command("player", CommandType.WAIT, index + 1))
                    self.ui.feedback = f"第 {index + 1} 拍已清空。"
                else:
                    self._choose_slot(index)
                return
        if EXECUTE_RECT.collidepoint(pos):
            self._execute()
        elif RESTART_RECT.collidepoint(pos):
            self._start_level()
        elif self.ui.selected_slot is not None:
            cell = GridPos((pos[0] - GRID_ORIGIN[0]) // CELL_SIZE, (pos[1] - GRID_ORIGIN[1]) // CELL_SIZE)
            if encounter.state.in_bounds(cell):
                self._assign_from_cell(cell)

    def _start_level(self) -> None:
        if self.load_error is not None:
            return
        if self._fixed_seed is not None:
            run_seed = self._fixed_seed
        elif self._random_rewards:
            run_seed = self._seed_source.getrandbits(63)
        else:
            run_seed = self.level_run.definition.seed
        self.level_run.restart(run_seed)
        self.scene = AppScene.BATTLE
        self.ui = Stage03UiState(feedback="先观察红色锁定格，再调整三拍顺序。")
        self._seed_opening_commands()
        self.events = self.level_run.encounter.preparation_events
        self.animation_started_ms = pygame.time.get_ticks()
        self.audio.play("click")

    def _seed_opening_commands(self) -> None:
        encounter_id = self.level_run.current_definition.encounter_id
        commands: list[Command]
        if encounter_id == "sequence_calibration":
            commands = [
                Command("player", CommandType.PUSH, 1, Direction.RIGHT),
                Command("player", CommandType.MOVE, 2, Direction.DOWN),
                Command("player", CommandType.PULL, 3, target_entity_id="charger_alpha"),
            ]
        elif encounter_id == "protocol_trial":
            commands = [
                Command("player", CommandType.PUSH, 1, Direction.RIGHT),
                Command("player", CommandType.MOVE, 2, Direction.RIGHT),
                Command("player", CommandType.WAIT, 3),
            ]
        else:
            commands = [
                Command("player", CommandType.PUSH, 1, Direction.RIGHT),
                Command("player", CommandType.MOVE, 2, Direction.DOWN),
                Command("player", CommandType.PULL, 3, target_entity_id="charger_prime"),
            ]
        for command in commands:
            self.level_run.encounter.set_command(command)

    def _choose_slot(self, index: int) -> None:
        if self.ui.selected_slot is None:
            self.ui.selected_slot = index
        elif self.ui.selected_slot == index:
            self.ui.selected_slot = None
        else:
            self.level_run.encounter.swap_slots(self.ui.selected_slot, index)
            self.ui.selected_slot = None
            self.ui.feedback = "顺序已改变；预演结果已同步刷新。"
            self.audio.play("click")

    def _assign_from_cell(self, cell: GridPos) -> None:
        state = self.level_run.encounter.state
        player = state.entities.get("player")
        if player is None:
            return
        target = state.entity_at(cell)
        delta = (cell.x - player.pos.x, cell.y - player.pos.y)
        direction = next((item for item in Direction if item.delta == delta), None)
        if cell == player.pos:
            self._assign(CommandType.SHIELD)
        elif target is not None and target.faction is Faction.ENEMY:
            if direction is not None:
                self._assign(CommandType.PUSH, direction=direction)
            elif (cell.x == player.pos.x or cell.y == player.pos.y) and player.pos.manhattan_distance(cell) <= self._visible_pull_range():
                self._assign(CommandType.PULL, target_id=target.entity_id)
            else:
                self.ui.feedback = f"牵引需要同一直线，当前最大距离 {self._visible_pull_range()} 格。"
        elif direction is not None:
            self._assign(CommandType.MOVE, direction=direction)
        else:
            self.ui.feedback = "移动与推击选择相邻格；远处直线敌人可被牵引。"

    def _visible_pull_range(self) -> int:
        return 3 if "vector_extender" in self.level_run.player_plugins else 2

    def _assign_nearest_pull(self) -> None:
        state = self.level_run.encounter.state
        player = state.entities.get("player")
        if player is None:
            return
        candidates = sorted(
            (
                entity
                for entity in state.entities.values()
                if entity.faction is Faction.ENEMY
                and (entity.pos.x == player.pos.x or entity.pos.y == player.pos.y)
                and player.pos.manhattan_distance(entity.pos) <= self._visible_pull_range()
            ),
            key=lambda entity: (player.pos.manhattan_distance(entity.pos), entity.entity_id),
        )
        if not candidates:
            self.ui.feedback = f"当前没有直线 {self._visible_pull_range()} 格内的牵引目标。"
            return
        self._assign(CommandType.PULL, target_id=candidates[0].entity_id)

    def _assign(
        self,
        command_type: CommandType,
        direction: Direction | None = None,
        target_id: str | None = None,
    ) -> None:
        if self.ui.selected_slot is None:
            return
        slot = self.ui.selected_slot + 1
        command = Command("player", command_type, slot, direction, target_id)
        self.level_run.encounter.set_command(command)
        self.ui.feedback = f"第 {slot} 拍：{self.command_label(command)}。"
        self.ui.selected_slot = None
        self.audio.play("click")

    def _execute(self) -> None:
        if self.scene is not AppScene.BATTLE or self.level_run.phase is not LevelPhase.BATTLE:
            return
        expected = state_fingerprint(self.preview.state)
        old_index = self.level_run.encounter_index
        resolution = self.level_run.confirm_turn()
        self.ui.verification_ok = state_fingerprint(resolution.result.state) == expected
        self.events = resolution.result.events + resolution.preparation_events
        self.animation_started_ms = pygame.time.get_ticks()
        self.ui.selected_slot = None
        self.audio.play("execute")
        if any(event.kind == "plugin_triggered" for event in self.events):
            self.audio.play("plugin")
        elif any(event.kind == "died" for event in self.events):
            self.audio.play("death")
        if self.level_run.phase is LevelPhase.REWARD:
            self.scene = AppScene.REWARD
            self.ui.reward_focus = 0
        elif self.level_run.phase in {LevelPhase.LEVEL_CLEAR, LevelPhase.DEFEAT}:
            self.scene = AppScene.RESULT
            if self.level_run.phase is LevelPhase.LEVEL_CLEAR:
                self.audio.play("victory")
        elif self.level_run.encounter_index != old_index:
            self._seed_opening_commands()
            self.events += self.level_run.encounter.preparation_events
            self.ui.feedback = "新遭遇已接入；生命与协议保留，敌人状态已重置。"
        else:
            self.ui.feedback = "回合已结算；敌人重新定位并公开下一轮意图。"

    def _choose_reward(self, index: int) -> None:
        choices = self.level_run.reward_choices
        if not 0 <= index < len(choices):
            return
        plugin = choices[index]
        self.level_run.choose_reward(plugin.plugin_id)
        self.scene = AppScene.BATTLE
        self.ui.selected_slot = None
        self.ui.feedback = f"{plugin.display_name} 已接入：{plugin.description}"
        self._seed_opening_commands()
        self.events = self.level_run.encounter.preparation_events
        self.animation_started_ms = pygame.time.get_ticks()
        self.audio.play("plugin")

    def active_event(self) -> LogicEvent | None:
        visible = [event for event in self.events if event.kind != "waited"]
        if not visible:
            return None
        index = (pygame.time.get_ticks() - self.animation_started_ms) // 230
        return visible[index] if 0 <= index < len(visible) else None

    def preview_label(self, slot: int) -> str:
        labels = [EVENT_LABELS.get(event.kind, event.kind) for event in self.preview.events if event.tick == slot]
        return " / ".join(labels) or "无事件"

    @staticmethod
    def command_label(command: Command) -> str:
        names = {
            CommandType.WAIT: "待机",
            CommandType.MOVE: "移动",
            CommandType.PUSH: "推击",
            CommandType.PULL: "牵引",
            CommandType.SHIELD: "护盾",
        }
        suffix = f" · {command.direction.name}" if command.direction is not None else f" · {command.target_entity_id}" if command.target_entity_id else ""
        return names[command.command_type] + suffix

    def _run_flow_smoke(self) -> None:
        from src.stage03_smoke import run_flow_smoke

        run_flow_smoke(self)

    def _script_turn(self, *commands: Command) -> None:
        for command in commands:
            self.level_run.encounter.set_command(command)
        self._execute()
