"""Formal action-first procedural run entry, preserving Stage03 as Showcase."""

from __future__ import annotations

import random
import warnings
from pathlib import Path

import pygame

from src.domain import (
    ActionRun,
    ActionRunPhase,
    Command,
    CommandType,
    Direction,
    Faction,
    GridPos,
    LogicEvent,
)
from src.infrastructure import (
    ContentLoadError,
    MetaProgress,
    load_demo_content,
    load_meta_progress,
    save_meta_progress,
)
from src.presentation.action_renderer import (
    ACTION_TUTORIAL_BACK_RECT,
    ACTION_TUTORIAL_REPLAY_RECT,
    ACTION_TUTORIAL_SKIP_ALL_RECT,
    ACTION_TUTORIAL_SKIP_STEP_RECT,
    NEW_RUN_RECT,
    REWARD_RECTS,
    SHOWCASE_RECT,
    TACTICAL_ACTION_RECTS,
    TACTICAL_CANCEL_RECT,
    TACTICAL_DOWN_RECT,
    TACTICAL_EXECUTE_RECT,
    TACTICAL_UP_RECT,
    WINDOW_SIZE,
    ActionRenderer,
)
from src.presentation.action_tutorial import ActionTutorial
from src.presentation.audio import CueAudio

MOVE_REPEAT_MS = 150
MOVE_INITIAL_REPEAT_MS = 190
MOVEMENT_KEYS = (
    pygame.K_w,
    pygame.K_a,
    pygame.K_s,
    pygame.K_d,
    pygame.K_UP,
    pygame.K_LEFT,
    pygame.K_DOWN,
    pygame.K_RIGHT,
)
KEY_DIRECTIONS = {
    pygame.K_w: Direction.UP,
    pygame.K_UP: Direction.UP,
    pygame.K_d: Direction.RIGHT,
    pygame.K_RIGHT: Direction.RIGHT,
    pygame.K_s: Direction.DOWN,
    pygame.K_DOWN: Direction.DOWN,
    pygame.K_a: Direction.LEFT,
    pygame.K_LEFT: Direction.LEFT,
}
SCANCODE_DIRECTIONS = {
    pygame.KSCAN_W: Direction.UP,
    pygame.KSCAN_UP: Direction.UP,
    pygame.KSCAN_D: Direction.RIGHT,
    pygame.KSCAN_RIGHT: Direction.RIGHT,
    pygame.KSCAN_S: Direction.DOWN,
    pygame.KSCAN_DOWN: Direction.DOWN,
    pygame.KSCAN_A: Direction.LEFT,
    pygame.KSCAN_LEFT: Direction.LEFT,
}
PLAYER_POSE_DURATIONS = {
    "move": 220,
    "attack": 260,
    "dodge": 320,
    "skill": 420,
    "hurt": 300,
}
REWARD_ACQUISITION_MS = 680

MIN_WINDOW_SIZE = (960, 600)


def initial_window_size(desktop_size: tuple[int, int]) -> tuple[int, int]:
    width, height = desktop_size
    if width <= 0 or height <= 0:
        return WINDOW_SIZE
    scale = min(1.0, width * 0.90 / WINDOW_SIZE[0], height * 0.85 / WINDOW_SIZE[1])
    result = (round(WINDOW_SIZE[0] * scale), round(WINDOW_SIZE[1] * scale))
    if width >= MIN_WINDOW_SIZE[0] and height >= MIN_WINDOW_SIZE[1]:
        result = (max(result[0], MIN_WINDOW_SIZE[0]), max(result[1], MIN_WINDOW_SIZE[1]))
    return (min(result[0], width), min(result[1], height))


class ActionApp:
    def __init__(
        self,
        smoke_test: bool = False,
        seed: int | None = None,
        seed_source: random.Random | None = None,
        data_root: Path | None = None,
        meta_path: Path | None = None,
    ) -> None:
        self.smoke_test = smoke_test
        self.fixed_seed = seed
        self.seed_source = seed_source or random.Random()
        self.meta_path = meta_path or (
            Path(__file__).resolve().parents[1] / "logs" / "meta_progress.json"
        )
        self.meta: MetaProgress = load_meta_progress(self.meta_path)
        self.run_state: ActionRun | None = None
        self.renderer: ActionRenderer | None = None
        self.screen: pygame.Surface | None = None
        self.audio = CueAudio()
        self.tutorial = ActionTutorial()
        self.selected_slot = 0
        self.reward_focus = 0
        self.reduced_motion = False
        self.debug_panel = False
        self.keyboard_focused = True
        self.input_notice = ""
        self.input_notice_until = 0
        self.flash_until: dict[str, int] = {}
        self.hit_marks: list[tuple[GridPos, int]] = []
        self.shot_trails: list[tuple[GridPos, GridPos, int]] = []
        self.dodge_trail: tuple[GridPos, GridPos, int] | None = None
        self.move_trails: list[tuple[GridPos, GridPos, int]] = []
        self.death_fragments: list[tuple[GridPos, int]] = []
        self.core_flash_until = 0
        self.reward_acquisition = None
        self.reward_acquired_until = 0
        self.unlock_just_earned = False
        self.launch_showcase = False
        self.load_error = ""
        self._result_recorded = False
        self._next_move_ms = 0
        self._held_movement_inputs: dict[tuple[str, int], Direction] = {}
        self.player_pose = "idle"
        self.player_pose_started_ms = 0
        self.player_pose_until_ms = 0
        self._tutorial_pending_new_run = False
        try:
            _, plugins = load_demo_content(data_root)
            self.plugins = plugins
        except ContentLoadError as exc:
            self.plugins = {}
            self.load_error = str(exc)

    def start_new_run(self) -> None:
        if self.load_error:
            return
        seed = (
            self.fixed_seed
            if self.fixed_seed is not None
            else self.seed_source.getrandbits(63)
        )
        self.run_state = ActionRun(
            seed,
            self.plugins,
            meta_core_bonus=self.meta.starting_core_bonus,
        )
        self.meta.last_seed = seed
        try:
            save_meta_progress(self.meta_path, self.meta)
        except OSError:
            pass
        self.selected_slot = 0
        self.reward_focus = 0
        self.unlock_just_earned = False
        self._result_recorded = False
        self.player_pose = "idle"
        self.player_pose_started_ms = 0
        self.player_pose_until_ms = 0
        self.reward_acquisition = None
        self.reward_acquired_until = 0
        self.shot_trails.clear()
        self._held_movement_inputs.clear()
        self.audio.play_music("battle")

    def run(self) -> int:
        pygame.init()
        try:
            desktops = pygame.display.get_desktop_sizes()
            desktop = desktops[0] if desktops else WINDOW_SIZE
            self.screen = pygame.display.set_mode(
                initial_window_size(desktop), pygame.RESIZABLE
            )
            pygame.display.set_caption("EchoZero | 动作 Roguelike + 战术因果编排")
            self.renderer = ActionRenderer(self.screen)
            self.keyboard_focused = bool(pygame.key.get_focused())
            if not self.keyboard_focused:
                self._focus_window()
            self.audio.initialise()
            self.audio.play_music("menu")
            if self.smoke_test and not self.load_error:
                self._run_smoke()
            clock = pygame.time.Clock()
            running = True
            frames = 0
            while running:
                dt = clock.tick(60) / 1000.0
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type in (pygame.KEYDOWN, pygame.KEYUP):
                        running = self._handle_keyboard_event(event) and running
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if not self.keyboard_focused:
                            self._focus_window()
                        self._handle_click(event.pos, event.button)
                    elif event.type == getattr(pygame, "WINDOWFOCUSLOST", -1):
                        self._handle_focus_lost()
                    elif event.type == getattr(pygame, "WINDOWFOCUSGAINED", -2):
                        self._handle_focus_gained()
                    elif event.type in {
                        getattr(pygame, name)
                        for name in (
                            "VIDEORESIZE",
                            "WINDOWRESIZED",
                            "WINDOWRESTORED",
                            "WINDOWSHOWN",
                            "WINDOWEXPOSED",
                            "WINDOWMAXIMIZED",
                        )
                        if hasattr(pygame, name)
                    }:
                        self._update_viewport()
                        if event.type in {
                            getattr(pygame, name)
                            for name in ("WINDOWRESTORED", "WINDOWSHOWN", "WINDOWMAXIMIZED")
                            if hasattr(pygame, name)
                        }:
                            self._focus_window()
                if not self.reward_acquisition_active:
                    self._continuous_movement()
                if (
                    self.run_state is not None
                    and not self.tutorial.active
                    and not self.reward_acquisition_active
                ):
                    events = self.run_state.update(dt)
                    self._consume(events)
                    self._record_result_if_needed()
                self._update_viewport()
                self.renderer.draw(self)
                pygame.display.flip()
                frames += 1
                if self.smoke_test and frames >= 2:
                    running = False
            return 2 if self.load_error else 0
        finally:
            pygame.quit()

    def _update_viewport(self) -> None:
        surface = pygame.display.get_surface()
        if surface is not None:
            self.screen = surface
            if self.renderer is not None:
                self.renderer.update_viewport_layout(surface)

    def _handle_focus_lost(self) -> None:
        self.keyboard_focused = False
        self._next_move_ms = 0
        self._held_movement_inputs.clear()

    def _handle_focus_gained(self) -> None:
        self.keyboard_focused = True
        self._next_move_ms = 0
        self._update_viewport()

    def _focus_window(self) -> None:
        try:
            from pygame._sdl2 import Window

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                Window.from_display_module().focus()
            self.keyboard_focused = True
        except (ImportError, pygame.error):
            self.keyboard_focused = bool(pygame.key.get_focused())
        self._next_move_ms = 0

    def _handle_keyboard_event(self, event: pygame.event.Event) -> bool:
        key = int(getattr(event, "key", 0))
        scancode = getattr(event, "scancode", None)
        direction = self._direction_for_input(key, scancode)
        input_id = self._movement_input_id(key, scancode)
        if event.type == pygame.KEYUP:
            if direction is not None:
                self._held_movement_inputs.pop(input_id, None)
            return True
        self.keyboard_focused = True
        if direction is not None:
            self._held_movement_inputs[input_id] = direction
        return self._handle_key(
            key,
            int(getattr(event, "mod", 0)),
            direction,
        )

    def _handle_key(
        self,
        key: int,
        mod: int,
        movement_direction: Direction | None = None,
    ) -> bool:
        if self.tutorial.active:
            return self._handle_tutorial_key(key, mod)
        if key == pygame.K_ESCAPE:
            return False
        if key == pygame.K_F2:
            self.reduced_motion = not self.reduced_motion
            return True
        if key == pygame.K_F3:
            self.debug_panel = not self.debug_panel
            self.audio.play("click")
            return True
        if self.reward_acquisition_active:
            return True
        if self.run_state is None:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self._request_new_run()
            elif key == pygame.K_F5:
                self.launch_showcase = True
                return False
            return True
        run = self.run_state
        if run.phase in {ActionRunPhase.VICTORY, ActionRunPhase.DEFEAT}:
            if key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r):
                self._request_new_run()
            return True
        if run.phase is ActionRunPhase.REWARD:
            if key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self._choose_reward(key - pygame.K_1)
            elif key in (pygame.K_LEFT, pygame.K_a):
                self.reward_focus = (self.reward_focus - 1) % 3
            elif key in (pygame.K_RIGHT, pygame.K_d):
                self.reward_focus = (self.reward_focus + 1) % 3
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self._choose_reward(self.reward_focus)
            return True
        if run.phase is ActionRunPhase.TACTICAL:
            return self._handle_tactical_key(key, movement_direction)
        if key == pygame.K_q:
            if run.enter_tactical():
                self.selected_slot = 0
                self.audio.play("inverse")
        elif key == pygame.K_c:
            mode = run.toggle_attack_mode()
            self._consume(run.last_events)
            self.input_notice = (
                "远程模式 · 3 格 / 半伤"
                if mode.value == "ranged"
                else "近战模式 · 1 格 / 全伤"
            )
            self.input_notice_until = pygame.time.get_ticks() + 900
            self.audio.play("slot")
        elif key in (pygame.K_SPACE, pygame.K_j):
            self._consume(run.attack())
        elif key == pygame.K_e:
            self._consume(run.tractor_skill())
        elif movement_direction is not None or key in MOVEMENT_KEYS:
            direction = movement_direction or self._direction_for_key(key)
            if mod & pygame.KMOD_SHIFT:
                self._consume(run.dodge(direction))
            else:
                self._consume(run.move_player(direction))
                self._next_move_ms = pygame.time.get_ticks() + MOVE_INITIAL_REPEAT_MS
        return True

    def _handle_tactical_key(
        self,
        key: int,
        movement_direction: Direction | None = None,
    ) -> bool:
        run = self.run_state
        assert run is not None
        if key == pygame.K_q:
            run.cancel_tactical()
            self.audio.play("cancel")
        elif pygame.K_1 <= key <= pygame.K_7:
            self.selected_slot = key - pygame.K_1
            self.audio.play("slot")
        elif key in (pygame.K_w, pygame.K_UP):
            self.selected_slot = run.move_tactical_action(self.selected_slot, -1)
            self.audio.play("slot")
        elif key in (pygame.K_s, pygame.K_DOWN):
            self.selected_slot = run.move_tactical_action(self.selected_slot, 1)
            self.audio.play("slot")
        elif key == pygame.K_RETURN:
            result = run.execute_tactical()
            if result is not None:
                self._consume(result.events)
                self.audio.play("confirm")
                self._record_result_if_needed()
        return True

    def _continuous_movement(self) -> None:
        run = self.run_state
        if (
            self.tutorial.active
            or run is None
            or run.phase is not ActionRunPhase.ACTION
        ):
            return
        now = pygame.time.get_ticks()
        if now < self._next_move_ms:
            return
        if self._held_movement_inputs:
            direction = tuple(self._held_movement_inputs.values())[-1]
            self._consume(run.move_player(direction))
            self._next_move_ms = now + MOVE_REPEAT_MS

    def _handle_click(self, pos: tuple[int, int], button: int) -> None:
        if button != 1 or self.renderer is None:
            return
        logical = self.renderer.to_logical(pos)
        if logical is None:
            return
        if self.tutorial.active:
            self._handle_tutorial_click(logical)
            return
        if self.reward_acquisition_active:
            return
        if self.run_state is None:
            if NEW_RUN_RECT.collidepoint(logical):
                self._request_new_run()
            elif SHOWCASE_RECT.collidepoint(logical):
                self.launch_showcase = True
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            return
        run = self.run_state
        if (
            run.phase is ActionRunPhase.ACTION
            and ACTION_TUTORIAL_REPLAY_RECT.collidepoint(logical)
        ):
            self._restart_action_tutorial()
            return
        if run.phase in {ActionRunPhase.VICTORY, ActionRunPhase.DEFEAT}:
            if NEW_RUN_RECT.collidepoint(logical):
                self._request_new_run()
            return
        if run.phase is ActionRunPhase.REWARD:
            for index, rect in enumerate(REWARD_RECTS):
                if rect.collidepoint(logical):
                    self._choose_reward(index)
                    return
            return
        if run.phase is ActionRunPhase.TACTICAL:
            for index, rect in enumerate(TACTICAL_ACTION_RECTS):
                if rect.collidepoint(logical):
                    self.selected_slot = index
                    return
            if TACTICAL_UP_RECT.collidepoint(logical):
                self.selected_slot = run.move_tactical_action(self.selected_slot, -1)
                return
            if TACTICAL_DOWN_RECT.collidepoint(logical):
                self.selected_slot = run.move_tactical_action(self.selected_slot, 1)
                return
            if TACTICAL_EXECUTE_RECT.collidepoint(logical):
                result = run.execute_tactical()
                if result is not None:
                    self._consume(result.events)
                    self._record_result_if_needed()
                return
            if TACTICAL_CANCEL_RECT.collidepoint(logical):
                run.cancel_tactical()
                return
            self._assign_tactical_from_grid(self.renderer.grid_pos(logical))
            return
        clicked = self.renderer.grid_pos(logical)
        player = run.player
        if player is not None:
            run.facing = self._dominant_direction(player.pos, clicked)
            self._consume(run.attack(run.facing))

    def _assign_tactical_from_grid(self, clicked: GridPos) -> None:
        run = self.run_state
        assert run is not None
        player = run.player
        if player is None or not run.state.in_bounds(clicked):
            return
        direction = self._dominant_direction(player.pos, clicked)
        run.facing = direction
        target = run.state.entity_at(clicked)
        if target is not None and target.faction is Faction.ENEMY:
            command_type = (
                CommandType.PUSH
                if target.pos.manhattan_distance(player.pos) == 1
                else CommandType.PULL
            )
            run.set_tactical_command(
                self.selected_slot + 1,
                Command(
                    "player", command_type, self.selected_slot + 1,
                    direction if command_type is CommandType.PUSH else None,
                    target.entity_id if command_type is CommandType.PULL else None,
                ),
            )
        elif clicked.manhattan_distance(player.pos) == 1:
            run.set_tactical_command(
                self.selected_slot + 1,
                Command("player", CommandType.MOVE, self.selected_slot + 1, direction),
            )

    def _choose_reward(self, index: int) -> None:
        run = self.run_state
        if run is None:
            return
        reward = run.choose_reward(index)
        self.reward_acquisition = reward
        duration = 320 if self.reduced_motion else REWARD_ACQUISITION_MS
        self.reward_acquired_until = pygame.time.get_ticks() + duration
        self.reward_focus = 0
        self.audio.play("reward")

    @property
    def reward_acquisition_active(self) -> bool:
        return (
            self.reward_acquisition is not None
            and pygame.time.get_ticks() < self.reward_acquired_until
        )

    def _request_new_run(self) -> None:
        if self.tutorial.completed_once:
            self.start_new_run()
            return
        self._tutorial_pending_new_run = True
        self.tutorial.start()
        self.audio.play("confirm")

    def _restart_action_tutorial(self) -> None:
        self._tutorial_pending_new_run = False
        self.tutorial.start()
        self.audio.play("click")

    def _handle_tutorial_key(self, key: int, mod: int) -> bool:
        if key == pygame.K_ESCAPE:
            self._cancel_action_tutorial()
        elif key == pygame.K_F2:
            self.reduced_motion = not self.reduced_motion
        elif key == pygame.K_F1:
            self.tutorial.skip_all()
            self._finish_action_tutorial()
        elif key == pygame.K_TAB and mod & pygame.KMOD_SHIFT:
            self.tutorial.back()
            self.audio.play("slot")
        elif key in (pygame.K_TAB, pygame.K_RETURN, pygame.K_SPACE):
            if self.tutorial.advance():
                self._finish_action_tutorial()
            else:
                self.audio.play("slot")
        return True

    def _handle_tutorial_click(self, logical: tuple[int, int]) -> None:
        if ACTION_TUTORIAL_BACK_RECT.collidepoint(logical):
            self.tutorial.back()
            self.audio.play("slot")
        elif ACTION_TUTORIAL_SKIP_ALL_RECT.collidepoint(logical):
            self.tutorial.skip_all()
            self._finish_action_tutorial()
        elif ACTION_TUTORIAL_SKIP_STEP_RECT.collidepoint(logical):
            if self.tutorial.skip_current():
                self._finish_action_tutorial()
            else:
                self.audio.play("slot")
        elif self.tutorial.advance():
            self._finish_action_tutorial()
        else:
            self.audio.play("slot")

    def _finish_action_tutorial(self) -> None:
        pending_new_run = self._tutorial_pending_new_run
        self._tutorial_pending_new_run = False
        self.audio.play("confirm")
        if pending_new_run:
            self.start_new_run()

    def _cancel_action_tutorial(self) -> None:
        self.tutorial.cancel()
        self._tutorial_pending_new_run = False
        self.audio.play("cancel")

    def _consume(self, events: tuple[LogicEvent, ...]) -> None:
        if not events:
            return
        now = pygame.time.get_ticks()
        flash_ms = 70 if self.reduced_motion else 135
        pose = ""
        pose_priority = -1
        for event in events:
            if (
                event.actor_id == "player"
                and event.from_pos is not None
                and event.to_pos is not None
                and (event.kind == "ranged_fired" or event.detail == "ranged_attack")
            ):
                self.shot_trails.append(
                    (event.from_pos, event.to_pos, now + (90 if self.reduced_motion else 220))
                )
            if event.kind in {"damaged", "shield_absorbed"} and event.target_id:
                self.flash_until[event.target_id] = now + flash_ms
            if event.kind == "damaged" and event.to_pos is not None:
                self.hit_marks.append((event.to_pos, now + flash_ms))
                if event.target_id == "player":
                    self.core_flash_until = now + (110 if self.reduced_motion else 260)
            if (
                event.kind == "moved"
                and event.actor_id == "player"
                and event.from_pos is not None
                and event.to_pos is not None
            ):
                self.move_trails.append(
                    (event.from_pos, event.to_pos, now + (60 if self.reduced_motion else 150))
                )
            if (
                event.kind == "dodged"
                and event.from_pos is not None
                and event.to_pos is not None
            ):
                self.dodge_trail = (event.from_pos, event.to_pos, now + (90 if self.reduced_motion else 220))
            if event.kind == "died" and event.to_pos is not None:
                self.death_fragments.append(
                    (event.to_pos, now + (120 if self.reduced_motion else 460))
                )
            if event.kind == "move_blocked":
                self.input_notice = "前方受阻"
                self.input_notice_until = now + 520
            if event.kind in {"damaged", "pushed", "enemy_charged"}:
                self.audio.play("impact")
            elif event.kind in {"moved", "enemy_moved", "dodged"}:
                self.audio.play("move")
            elif event.kind == "pulled":
                self.audio.play("pull")
            elif event.kind == "shielded":
                self.audio.play("shield")
            elif event.kind == "died":
                self.audio.play("death")
            candidate = ""
            priority = -1
            if event.kind == "dodged" and event.actor_id == "player":
                candidate, priority = "dodge", 5
            elif event.kind in {"pulled", "pull_missed"} or event.detail == "tractor_skill":
                candidate, priority = "skill", 4
            elif (
                event.actor_id == "player"
                and (
                    event.kind in {"attack_missed", "ranged_fired"}
                    or event.detail in {"basic_attack", "ranged_attack", "collision"}
                )
            ):
                candidate, priority = "attack", 3
            elif event.kind == "damaged" and event.target_id == "player":
                candidate, priority = "hurt", 2
            elif event.kind == "moved" and event.actor_id == "player":
                candidate, priority = "move", 1
            if priority > pose_priority:
                pose, pose_priority = candidate, priority
        if pose:
            self._set_player_pose(pose, now)
        self.hit_marks = [
            (position, until) for position, until in self.hit_marks if until > now
        ]
        self.move_trails = [trail for trail in self.move_trails if trail[2] > now]
        self.shot_trails = [trail for trail in self.shot_trails if trail[2] > now]
        self.death_fragments = [
            fragment for fragment in self.death_fragments if fragment[1] > now
        ]

    def _set_player_pose(self, pose: str, now: int | None = None) -> None:
        started = pygame.time.get_ticks() if now is None else now
        duration = PLAYER_POSE_DURATIONS.get(pose, 180)
        if self.reduced_motion:
            duration = min(duration, 100)
        self.player_pose = pose
        self.player_pose_started_ms = started
        self.player_pose_until_ms = started + duration

    def player_pose_frame(self, now: int) -> tuple[str, float]:
        if now >= self.player_pose_until_ms:
            return ("idle", (now % 1200) / 1200)
        duration = max(1, self.player_pose_until_ms - self.player_pose_started_ms)
        return (
            self.player_pose,
            max(0.0, min(1.0, (now - self.player_pose_started_ms) / duration)),
        )

    def _record_result_if_needed(self) -> None:
        run = self.run_state
        if (
            run is None
            or run.phase not in {ActionRunPhase.VICTORY, ActionRunPhase.DEFEAT}
            or self._result_recorded
        ):
            return
        self._result_recorded = True
        self.unlock_just_earned = self.meta.record_result(
            run.phase is ActionRunPhase.VICTORY
        )
        try:
            save_meta_progress(self.meta_path, self.meta)
        except OSError:
            pass
        self.audio.play_music("final")
        self.audio.play("demo_clear" if run.phase is ActionRunPhase.VICTORY else "death")

    def _run_smoke(self) -> None:
        self._request_new_run()
        while self.tutorial.active:
            finished = self.tutorial.advance()
            if finished:
                self._finish_action_tutorial()
        assert self.run_state is not None
        for encounter in range(self.run_state.ENCOUNTER_COUNT):
            for enemy in self.run_state.active_enemies:
                self.run_state.state.entities.pop(enemy.entity_id, None)
            self.run_state.update(0.01)
            if encounter < self.run_state.ENCOUNTER_COUNT - 1:
                self.run_state.choose_reward(0)
        self._record_result_if_needed()

    def _nearest_aligned_enemy(self, direction: Direction) -> str | None:
        run = self.run_state
        if run is None or run.player is None:
            return None
        player = run.player
        candidates = []
        for enemy in run.active_enemies:
            dx = enemy.pos.x - player.pos.x
            dy = enemy.pos.y - player.pos.y
            vx, vy = direction.delta
            if (vx and dy == 0 and dx * vx > 0) or (vy and dx == 0 and dy * vy > 0):
                candidates.append(enemy)
        if not candidates:
            return None
        return min(candidates, key=lambda item: item.pos.manhattan_distance(player.pos)).entity_id

    @staticmethod
    def _direction_for_key(key: int) -> Direction:
        return KEY_DIRECTIONS[key]

    @staticmethod
    def _direction_for_input(key: int, scancode: int | None) -> Direction | None:
        if scancode is not None and scancode in SCANCODE_DIRECTIONS:
            return SCANCODE_DIRECTIONS[scancode]
        return KEY_DIRECTIONS.get(key)

    @staticmethod
    def _movement_input_id(key: int, scancode: int | None) -> tuple[str, int]:
        if scancode is not None:
            return ("scancode", int(scancode))
        return ("key", key)

    @staticmethod
    def _dominant_direction(origin: GridPos, target: GridPos) -> Direction:
        dx = target.x - origin.x
        dy = target.y - origin.y
        if abs(dx) >= abs(dy):
            return Direction.RIGHT if dx >= 0 else Direction.LEFT
        return Direction.DOWN if dy >= 0 else Direction.UP
