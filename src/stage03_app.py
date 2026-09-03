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
    CombatState,
    Direction,
    Faction,
    GridPos,
    LevelPhase,
    LevelRun,
    LogicEvent,
    PluginDefinition,
    SimulationResult,
    state_fingerprint,
)
from src.infrastructure import ContentLoadError, load_demo_content
from src.infrastructure.session_metrics import SessionMetrics
from src.presentation.audio import CueAudio
from src.presentation.battle_view import (
    BattleView,
    command_display_label,
    meaningful_rewrite,
)
from src.presentation.effects import (
    CAUSALITY_MS,
    EXECUTE_PREP_MS,
    EXECUTE_RESULT_MS,
    REDUCED_CAUSALITY_MS,
    REDUCED_PREP_MS,
    REDUCED_RESULT_MS,
    REDUCED_REWARD_MS,
    REWARD_ACQUIRE_MS,
    PresentationFrame,
    cue_for_event,
    playback_state,
    presentation_duration_ms,
    presentation_frame,
)
from src.presentation.tutorial import ContextualTutorial
from src.presentation.stage03_renderer import (
    CELL_SIZE,
    EXECUTE_RECT,
    GRID_ORIGIN,
    MENU_START_RECT,
    PROTOCOL_RECT,
    RESTART_RECT,
    RESULT_RESTART_RECT,
    REWARD_RECTS,
    SLOT_RECTS,
    TUTORIAL_REPLAY_RECT,
    TUTORIAL_SKIP_ALL_RECT,
    TUTORIAL_SKIP_STEP_RECT,
    WINDOW_SIZE,
    EVENT_LABELS,
    Stage03Renderer,
)


class AppScene(str, Enum):
    MENU = "menu"
    BATTLE = "battle"
    REWARD = "reward"
    TRANSITION = "transition"
    RESULT = "result"
    ERROR = "error"


VIEWPORT_REFRESH_EVENT_TYPES = frozenset(
    event_type
    for event_name in (
        "VIDEORESIZE",
        "WINDOWRESIZED",
        "WINDOWSIZECHANGED",
        "WINDOWRESTORED",
        "WINDOWSHOWN",
        "WINDOWEXPOSED",
        "WINDOWMAXIMIZED",
        "WINDOWFOCUSGAINED",
    )
    if isinstance((event_type := getattr(pygame, event_name, None)), int)
)
MIN_WINDOW_SIZE = (960, 600)
INITIAL_DESKTOP_WIDTH_RATIO = 0.90
INITIAL_DESKTOP_HEIGHT_RATIO = 0.85


def initial_window_size(desktop_size: tuple[int, int]) -> tuple[int, int]:
    """Choose a visible 16:10 client area while leaving room for native chrome."""
    desktop_width, desktop_height = desktop_size
    if desktop_width <= 0 or desktop_height <= 0:
        return WINDOW_SIZE
    width_limit = max(1, round(desktop_width * INITIAL_DESKTOP_WIDTH_RATIO))
    height_limit = max(1, round(desktop_height * INITIAL_DESKTOP_HEIGHT_RATIO))
    scale = min(1.0, width_limit / WINDOW_SIZE[0], height_limit / WINDOW_SIZE[1])
    width = max(1, round(WINDOW_SIZE[0] * scale))
    height = max(1, round(WINDOW_SIZE[1] * scale))
    if desktop_width >= MIN_WINDOW_SIZE[0] and desktop_height >= MIN_WINDOW_SIZE[1]:
        width = max(width, MIN_WINDOW_SIZE[0])
        height = max(height, MIN_WINDOW_SIZE[1])
    return (min(width, desktop_width), min(height, desktop_height))


@dataclass
class Stage03UiState:
    selected_slot: int | None = None
    reward_focus: int = 0
    debug: bool = False
    reduced_motion: bool = False
    muted: bool = False
    volume_percent: int = 65
    verification_ok: bool | None = None
    feedback: str = "选择命令槽，再点击战场目标。"
    hovered_slot: int | None = None
    protocol_hovered: bool = False
    swap_pair: tuple[int, int] | None = None
    swap_started_ms: int = 0


class Stage03App:
    def __init__(
        self,
        smoke_test: bool = False,
        data_root: Path | None = None,
        seed: int | None = None,
        random_rewards: bool = False,
        rng: random.Random | None = None,
        metrics_path: Path | None = None,
    ) -> None:
        self.smoke_test = smoke_test
        self.screen: pygame.Surface | None = None
        self.renderer: Stage03Renderer | None = None
        self.audio = CueAudio()
        self.tutorial = ContextualTutorial()
        self.metrics = SessionMetrics()
        self.metrics_path = metrics_path or (
            Path(__file__).resolve().parents[1] / "logs" / "session_summary.txt"
        )
        self.metrics_error: str | None = None
        self.scene = AppScene.MENU
        self.ui = Stage03UiState()
        self.events: tuple[LogicEvent, ...] = ()
        self.animation_started_ms = 0
        self._last_audio_event_index: int | None = None
        self.load_error: str | None = None
        self._fixed_seed = seed
        self._random_rewards = random_rewards
        self._seed_source = rng or random.Random()
        self._has_started_run = False
        self._last_execute_click_ms = -1000
        self._execution_view: BattleView | None = None
        self._post_execute_scene = AppScene.BATTLE
        self._post_execute_events: tuple[LogicEvent, ...] = ()
        self._causality_rewrite = False
        self._causality_baseline: CombatState | None = None
        self._pending_reward_index: int | None = None
        self._reward_started_ms = 0
        try:
            levels, plugins = load_demo_content(data_root)
            self.level_definitions = levels
            self.plugin_definitions = plugins
            self.level_index = 0
            initial_seed = seed if seed is not None else levels[0].seed
            self.level_run = LevelRun(levels[0], plugins, initial_seed)
        except ContentLoadError as exc:
            self.load_error = str(exc)
            self.scene = AppScene.ERROR

    def run(self) -> int:
        pygame.init()
        try:
            desktop_sizes = pygame.display.get_desktop_sizes()
            desktop_size = desktop_sizes[0] if desktop_sizes else WINDOW_SIZE
            self.screen = pygame.display.set_mode(
                initial_window_size(desktop_size),
                pygame.RESIZABLE,
            )
            pygame.display.set_caption("EchoZero | Tactical Causality")
            self.renderer = Stage03Renderer(self.screen)
            pygame.event.pump()
            self.update_viewport_layout()
            self.audio.initialise()
            self.audio.play_music("menu")
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
                    elif event.type == pygame.MOUSEMOTION:
                        self._handle_motion(event.pos)
                    elif event.type == pygame.WINDOWFOCUSLOST:
                        self._handle_focus_lost()
                    elif event.type in VIEWPORT_REFRESH_EVENT_TYPES:
                        self.update_viewport_layout()
                self._update_presentation_state()
                self._update_presentation_audio()
                self.update_viewport_layout()
                self.renderer.draw(self)
                pygame.display.flip()
                frames += 1
                if self.smoke_test and frames >= 2:
                    running = False
                clock.tick(60)
            return 2 if self.load_error is not None else 0
        finally:
            self._sync_tutorial_metrics()
            try:
                self.metrics.write(self.metrics_path)
            except OSError as exc:
                self.metrics_error = str(exc)
            pygame.quit()

    def update_viewport_layout(self) -> None:
        """Synchronise layout with pygame's current client surface."""
        current_surface = pygame.display.get_surface()
        if current_surface is None:
            return
        self.screen = current_surface
        if self.renderer is not None:
            self.renderer.update_viewport_layout(current_surface)

    @property
    def preview(self) -> SimulationResult:
        return self.battle_view.preview

    @property
    def battle_view(self) -> BattleView:
        if self._execution_view is not None:
            return self._execution_view
        run = self.level_run
        return BattleView(
            run.encounter.state,
            tuple(run.encounter.commands),
            run.encounter.preview(),
            run.current_definition,
            run.definition.display_name,
            self.level_index + 1,
            run.progress,
            run.build_summary,
            run.plugin_definitions,
            run.run_seed,
        )

    @property
    def visual_state(self) -> CombatState:
        view = self.battle_view
        if self._execution_view is None:
            return view.state
        return playback_state(view.state, self.events, self.presentation)

    @property
    def execution_active(self) -> bool:
        return self._execution_view is not None

    @property
    def execution_elapsed_ms(self) -> int:
        return max(0, pygame.time.get_ticks() - self.animation_started_ms)

    @property
    def execution_phase(self) -> str:
        if not self.execution_active:
            return ""
        prep = REDUCED_PREP_MS if self.ui.reduced_motion else EXECUTE_PREP_MS
        result = REDUCED_RESULT_MS if self.ui.reduced_motion else EXECUTE_RESULT_MS
        event_end = prep + presentation_duration_ms(self.events, self.ui.reduced_motion)
        elapsed = self.execution_elapsed_ms
        if elapsed < prep:
            return "prepare"
        if elapsed < event_end:
            return "beats"
        if elapsed < event_end + result:
            return "result"
        return "rewrite" if self._causality_rewrite else "complete"

    @property
    def causality_rewrite_visible(self) -> bool:
        return self.execution_phase == "rewrite"

    @property
    def causality_rewrite_progress(self) -> float:
        if not self.causality_rewrite_visible:
            return 0.0
        prep = REDUCED_PREP_MS if self.ui.reduced_motion else EXECUTE_PREP_MS
        result = REDUCED_RESULT_MS if self.ui.reduced_motion else EXECUTE_RESULT_MS
        start = prep + presentation_duration_ms(self.events, self.ui.reduced_motion) + result
        duration = REDUCED_CAUSALITY_MS if self.ui.reduced_motion else CAUSALITY_MS
        return min(1.0, max(0.0, (self.execution_elapsed_ms - start) / duration))

    @property
    def reward_acquisition(self) -> PluginDefinition | None:
        if self._pending_reward_index is None:
            return None
        return self.level_run.reward_choices[self._pending_reward_index]

    @property
    def reward_animation_progress(self) -> float:
        if self._pending_reward_index is None:
            return 0.0
        duration = REDUCED_REWARD_MS if self.ui.reduced_motion else REWARD_ACQUIRE_MS
        return min(1.0, (pygame.time.get_ticks() - self._reward_started_ms) / duration)

    def _handle_key(self, key: int) -> bool:
        if key == pygame.K_ESCAPE:
            return False
        if self.tutorial.active:
            if key == pygame.K_F1:
                self._skip_all_tutorial()
            elif key == pygame.K_TAB:
                self._advance_tutorial()
            return True
        if key == pygame.K_m:
            self.ui.muted = not self.ui.muted
            self.audio.set_muted(self.ui.muted)
            self.ui.feedback = "音频已关闭。" if self.ui.muted else "音频已开启。"
            self.audio.play("click")
            return True
        if key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.ui.volume_percent = max(0, self.ui.volume_percent - 10)
            self.audio.set_volume(self.ui.volume_percent / 100)
            self.ui.feedback = f"主音量 {self.ui.volume_percent}%。"
            return True
        if key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
            self.ui.volume_percent = min(100, self.ui.volume_percent + 10)
            self.audio.set_volume(self.ui.volume_percent / 100)
            self.ui.feedback = f"主音量 {self.ui.volume_percent}%。"
            self.audio.play("click")
            return True
        if key == pygame.K_F2:
            self.ui.reduced_motion = not self.ui.reduced_motion
            self.ui.feedback = "减弱动态已开启。" if self.ui.reduced_motion else "完整动态已开启。"
            return True
        if self.scene is AppScene.MENU:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self._start_level()
            return True
        if self.scene is AppScene.RESULT:
            if key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r):
                self._start_level()
            return True
        if self.scene is AppScene.TRANSITION:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self._start_next_level()
            elif key == pygame.K_r:
                self._start_level()
            return True
        if self.scene is AppScene.REWARD:
            if self._pending_reward_index is not None:
                return True
            if key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self._choose_reward(key - pygame.K_1)
            elif key in (pygame.K_LEFT, pygame.K_a):
                self.ui.reward_focus = (self.ui.reward_focus - 1) % len(self.level_run.reward_choices)
                self.audio.play("hover")
            elif key in (pygame.K_RIGHT, pygame.K_d):
                self.ui.reward_focus = (self.ui.reward_focus + 1) % len(self.level_run.reward_choices)
                self.audio.play("hover")
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self._choose_reward(self.ui.reward_focus)
            elif key == pygame.K_r:
                self._start_level()
            return True
        if self.scene is not AppScene.BATTLE:
            return True
        if self.execution_active:
            if key == pygame.K_r:
                self._start_level()
            return True
        if key in (pygame.K_1, pygame.K_2, pygame.K_3):
            self._choose_slot(key - pygame.K_1)
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            self._execute()
        elif key == pygame.K_r:
            self._start_level()
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

    def _handle_motion(self, pos: tuple[int, int]) -> None:
        logical = self.renderer.to_logical(pos) if self.renderer is not None else pos
        if logical is None:
            self.ui.hovered_slot = None
            self.ui.protocol_hovered = False
            return
        pos = logical
        self.ui.protocol_hovered = self.scene is AppScene.BATTLE and PROTOCOL_RECT.collidepoint(pos)
        if self.scene is AppScene.BATTLE:
            self.ui.hovered_slot = next(
                (index for index, rect in enumerate(SLOT_RECTS) if rect.collidepoint(pos)),
                None,
            )
            return
        self.ui.hovered_slot = None
        if self.scene is not AppScene.REWARD or self._pending_reward_index is not None:
            return
        for index, rect in enumerate(REWARD_RECTS[: len(self.level_run.reward_choices)]):
            if rect.collidepoint(pos):
                if index != self.ui.reward_focus:
                    self.audio.play("hover")
                self.ui.reward_focus = index
                return

    def _handle_click(self, pos: tuple[int, int], button: int) -> None:
        logical = self.renderer.to_logical(pos) if self.renderer is not None else pos
        if logical is None:
            return
        pos = logical
        if self.tutorial.active:
            if button != 1:
                return
            if TUTORIAL_SKIP_ALL_RECT.collidepoint(pos):
                self._skip_all_tutorial()
            elif TUTORIAL_SKIP_STEP_RECT.collidepoint(pos):
                self._skip_tutorial_step()
            else:
                self._advance_tutorial()
            return
        if button != 1 and not (self.scene is AppScene.BATTLE and button == 3):
            return
        if self.scene is AppScene.MENU and MENU_START_RECT.collidepoint(pos):
            self._start_level()
        elif self.scene is AppScene.RESULT and RESULT_RESTART_RECT.collidepoint(pos):
            self._start_level()
        elif self.scene is AppScene.TRANSITION and RESULT_RESTART_RECT.collidepoint(pos):
            self._start_next_level()
        elif self.scene is AppScene.REWARD:
            for index, rect in enumerate(REWARD_RECTS[: len(self.level_run.reward_choices)]):
                if rect.collidepoint(pos):
                    self._choose_reward(index)
                    return
        elif self.scene is AppScene.BATTLE:
            if button == 1 and TUTORIAL_REPLAY_RECT.collidepoint(pos):
                self._restart_tutorial()
                return
            self._handle_battle_click(pos, button)

    def _handle_battle_click(self, pos: tuple[int, int], button: int) -> None:
        if self.execution_active:
            if RESTART_RECT.collidepoint(pos):
                self._start_level()
            return
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
            if self._accept_execute_click():
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
        if self._has_started_run:
            self.metrics.record_retry()
        self._has_started_run = True
        muted = self.ui.muted
        reduced_motion = self.ui.reduced_motion
        volume_percent = self.ui.volume_percent
        if self._fixed_seed is not None:
            run_seed = self._fixed_seed
        elif self._random_rewards:
            run_seed = self._seed_source.getrandbits(63)
        else:
            run_seed = self.level_run.definition.seed
        self.level_index = 0
        self.level_run = LevelRun(
            self.level_definitions[0], self.plugin_definitions, run_seed
        )
        self.metrics.start_run(run_seed)
        self.scene = AppScene.BATTLE
        self.ui = Stage03UiState(
            feedback="",
            muted=muted,
            reduced_motion=reduced_motion,
            volume_percent=volume_percent,
        )
        self._seed_opening_commands()
        self.events = self.level_run.encounter.preparation_events
        self.animation_started_ms = pygame.time.get_ticks()
        self._last_audio_event_index = None
        self._last_execute_click_ms = -1000
        self._execution_view = None
        self._post_execute_events = ()
        self._post_execute_scene = AppScene.BATTLE
        self._pending_reward_index = None
        self._causality_rewrite = False
        self.tutorial.begin_initial()
        self._sync_tutorial_metrics()
        self._snapshot_metrics()
        self.audio.play_music("battle")
        self.audio.play("click")
        self._capture_causality_baseline()

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
        elif encounter_id == "dual_lock_climax":
            commands = [
                Command("player", CommandType.PUSH, 1, Direction.RIGHT),
                Command("player", CommandType.MOVE, 2, Direction.DOWN),
                Command("player", CommandType.PULL, 3, target_entity_id="charger_prime"),
            ]
        else:
            commands = [
                Command("player", CommandType.WAIT, slot) for slot in range(1, 4)
            ]
        for command in commands:
            self.level_run.encounter.set_command(command)

    def _choose_slot(self, index: int) -> None:
        if self.ui.selected_slot is None:
            self.ui.selected_slot = index
        elif self.ui.selected_slot == index:
            self.ui.selected_slot = None
        else:
            first = self.ui.selected_slot
            self.level_run.encounter.swap_slots(first, index)
            self.ui.swap_pair = (first, index)
            self.ui.swap_started_ms = pygame.time.get_ticks()
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
        self.audio.play("slot")

    def _execute(self) -> None:
        if (
            self.scene is not AppScene.BATTLE
            or self.level_run.phase is not LevelPhase.BATTLE
            or self.execution_active
        ):
            return
        encounter = self.level_run.encounter
        planned_preview = encounter.preview()
        expected = state_fingerprint(planned_preview.state)
        old_index = self.level_run.encounter_index
        encounter_id = self.level_run.current_definition.encounter_id
        execution_view = BattleView(
            encounter.state.clone(),
            tuple(encounter.commands),
            planned_preview,
            self.level_run.current_definition,
            self.level_run.definition.display_name,
            self.level_index + 1,
            self.level_run.progress,
            self.level_run.build_summary,
            self.level_run.plugin_definitions,
            self.level_run.run_seed,
        )
        resolution = self.level_run.confirm_turn()
        self.ui.verification_ok = state_fingerprint(resolution.result.state) == expected
        self.events = resolution.result.events
        self.animation_started_ms = pygame.time.get_ticks()
        self._last_audio_event_index = None
        self.ui.selected_slot = None
        self.audio.play("confirm")
        self._sync_tutorial_metrics()
        resolved_player = resolution.result.state.entities.get("player")
        self.metrics.record_turn(
            self.level_index + 1,
            encounter_id,
            max(0, resolution.result.state.turn - 1),
            resolved_player.hp if resolved_player is not None else 0,
            tuple(self.level_run.player_plugins),
            resolution.outcome.value,
        )
        target_scene = AppScene.BATTLE
        if self.level_run.phase is LevelPhase.REWARD:
            target_scene = AppScene.REWARD
            self.ui.reward_focus = 0
        elif self.level_run.phase is LevelPhase.DEFEAT:
            target_scene = AppScene.RESULT
        elif self.level_run.phase is LevelPhase.LEVEL_CLEAR:
            if self.level_index + 1 < len(self.level_definitions):
                target_scene = AppScene.TRANSITION
            else:
                target_scene = AppScene.RESULT
            self.audio.play("level_clear" if self.level_index == 0 else "demo_clear")
        elif self.level_run.encounter_index != old_index:
            self._seed_opening_commands()
            self.events += self.level_run.encounter.preparation_events
            if (
                self.level_index == 1
                and self.level_run.encounter_index
                == len(self.level_run.definition.encounters) - 1
            ):
                self.audio.play_music("final")
            self.ui.feedback = "新遭遇已接入；生命与协议保留，敌人状态已重置。"
        else:
            self.ui.feedback = "回合已结算；有效三拍已保留，失效目标已改为追击建议。"
        self._causality_rewrite = meaningful_rewrite(
            self._causality_baseline,
            resolution.result.state,
            resolution.result.events,
        )
        animate = self.renderer is not None and not self.smoke_test
        if animate:
            self._execution_view = execution_view
            self._post_execute_events = resolution.preparation_events
            self._post_execute_scene = target_scene
            self.scene = AppScene.BATTLE
        else:
            self.events += resolution.preparation_events
            self.scene = target_scene
            self._causality_rewrite = False
            if target_scene is AppScene.BATTLE:
                self._capture_causality_baseline()
        self._snapshot_metrics()

    def _choose_reward(self, index: int) -> None:
        choices = self.level_run.reward_choices
        if not 0 <= index < len(choices) or self._pending_reward_index is not None:
            return
        self.ui.reward_focus = index
        if self.renderer is not None and not self.smoke_test:
            self._pending_reward_index = index
            self._reward_started_ms = pygame.time.get_ticks()
            self.audio.play("confirm")
            return
        self._commit_reward(index)

    def _commit_reward(self, index: int) -> None:
        plugin = self.level_run.reward_choices[index]
        self.level_run.choose_reward(plugin.plugin_id)
        self._pending_reward_index = None
        self.scene = AppScene.BATTLE
        self.ui.selected_slot = None
        self.ui.feedback = f"{plugin.display_name} 已接入：{plugin.description}"
        self._seed_opening_commands()
        self.events = self.level_run.encounter.preparation_events
        self.animation_started_ms = pygame.time.get_ticks()
        self._last_audio_event_index = None
        self._snapshot_metrics()
        self.audio.play("reward")
        self._capture_causality_baseline()

    def _start_next_level(self) -> None:
        if self.level_index + 1 >= len(self.level_definitions):
            return
        inherited_hp = self.level_run.player_hp
        inherited_plugins = tuple(self.level_run.player_plugins)
        run_seed = self.level_run.run_seed
        self.level_index += 1
        self.level_run = LevelRun(
            self.level_definitions[self.level_index],
            self.plugin_definitions,
            run_seed,
            initial_player_hp=inherited_hp,
            initial_plugins=inherited_plugins,
        )
        self.scene = AppScene.BATTLE
        self.ui = Stage03UiState(
            feedback="逆相反应堆在线：先看规则方向，再编排三拍。",
            muted=self.ui.muted,
            reduced_motion=self.ui.reduced_motion,
            volume_percent=self.ui.volume_percent,
        )
        self.events = self.level_run.encounter.preparation_events
        self.animation_started_ms = pygame.time.get_ticks()
        self._last_audio_event_index = None
        self._execution_view = None
        self._post_execute_events = ()
        self._post_execute_scene = AppScene.BATTLE
        self._pending_reward_index = None
        self._snapshot_metrics()
        self.audio.play_music("battle")
        self.audio.play("inverse")
        self._capture_causality_baseline()

    def active_event(self) -> LogicEvent | None:
        return self.presentation.event

    @property
    def presentation(self) -> PresentationFrame:
        elapsed = pygame.time.get_ticks() - self.animation_started_ms
        if self.execution_active:
            prep = REDUCED_PREP_MS if self.ui.reduced_motion else EXECUTE_PREP_MS
            if elapsed < prep:
                return PresentationFrame(None, None, 0.0, (0, 0), 0.0, 0)
            elapsed -= prep
        return presentation_frame(self.events, elapsed, self.ui.reduced_motion)

    def _update_presentation_state(self) -> None:
        if self.execution_active:
            prep = REDUCED_PREP_MS if self.ui.reduced_motion else EXECUTE_PREP_MS
            result = REDUCED_RESULT_MS if self.ui.reduced_motion else EXECUTE_RESULT_MS
            rewrite = 0
            if self._causality_rewrite:
                rewrite = (
                    REDUCED_CAUSALITY_MS
                    if self.ui.reduced_motion
                    else CAUSALITY_MS
                )
            total = (
                prep
                + presentation_duration_ms(self.events, self.ui.reduced_motion)
                + result
                + rewrite
            )
            if self.execution_elapsed_ms >= total:
                target_scene = self._post_execute_scene
                post_events = self._post_execute_events
                self._execution_view = None
                self._post_execute_events = ()
                self._post_execute_scene = AppScene.BATTLE
                self._causality_rewrite = False
                self.scene = target_scene
                self.events = post_events
                self.animation_started_ms = pygame.time.get_ticks()
                self._last_audio_event_index = None
                if target_scene is AppScene.BATTLE:
                    self._capture_causality_baseline()
        if self._pending_reward_index is not None:
            duration = (
                REDUCED_REWARD_MS
                if self.ui.reduced_motion
                else REWARD_ACQUIRE_MS
            )
            if pygame.time.get_ticks() - self._reward_started_ms >= duration:
                index = self._pending_reward_index
                self._commit_reward(index)

    def _update_presentation_audio(self) -> None:
        frame = self.presentation
        if (
            frame.event is None
            or frame.event_index is None
            or frame.event_index == self._last_audio_event_index
        ):
            return
        self._last_audio_event_index = frame.event_index
        cue = cue_for_event(frame.event)
        if cue is not None:
            self.audio.play(cue)

    def preview_label(self, slot: int) -> str:
        labels = [EVENT_LABELS.get(event.kind, "战术事件") for event in self.preview.events if event.tick == slot]
        return " / ".join(labels) or "无事件"

    def command_label(self, command: Command) -> str:
        return command_display_label(command, self.battle_view)

    def _run_flow_smoke(self) -> None:
        from src.stage03_smoke import run_flow_smoke

        run_flow_smoke(self)

    def _script_turn(self, *commands: Command) -> None:
        for command in commands:
            self.level_run.encounter.set_command(command)
        self._execute()

    def _advance_tutorial(self) -> None:
        if self.tutorial.current is None:
            return
        self.tutorial.advance()
        self._sync_tutorial_metrics()
        if not self.tutorial.active:
            self.ui.feedback = ""

    def _skip_tutorial_step(self) -> None:
        self.tutorial.skip_current()
        self._sync_tutorial_metrics()
        if not self.tutorial.active:
            self.ui.feedback = ""

    def _skip_all_tutorial(self) -> None:
        self.tutorial.skip_all()
        self._sync_tutorial_metrics()
        self.ui.feedback = ""

    def _restart_tutorial(self) -> None:
        if self.scene is not AppScene.BATTLE or self.execution_active:
            return
        self.ui.selected_slot = None
        self.tutorial.restart()
        self._sync_tutorial_metrics()
        self.ui.feedback = "已重新进入模拟教学；战斗状态不会改变。"

    def _sync_tutorial_metrics(self) -> None:
        self.metrics.sync_tutorial(self.tutorial.shown, self.tutorial.skipped)

    def _snapshot_metrics(self) -> None:
        if self.load_error is not None:
            return
        player = self.level_run.encounter.state.entities.get("player")
        self.metrics.snapshot(
            self.level_index + 1,
            self.level_run.current_definition.encounter_id,
            max(0, self.level_run.encounter.state.turn - 1),
            player.hp if player is not None else 0,
            tuple(self.level_run.player_plugins),
        )

    def _capture_causality_baseline(self) -> None:
        if self.level_run.phase is LevelPhase.BATTLE:
            self._causality_baseline = self.level_run.encounter.preview().state.clone()
        else:
            self._causality_baseline = None

    def _handle_focus_lost(self) -> None:
        self.ui.selected_slot = None
        self.ui.feedback = "窗口失焦：已取消槽位选择，战斗不会自动执行。"

    def _accept_execute_click(self) -> bool:
        now = pygame.time.get_ticks()
        if now - self._last_execute_click_ms < 180:
            self.ui.feedback = "已忽略连续点击；请先查看本回合因果反馈。"
            return False
        self._last_execute_click_ms = now
        return True
