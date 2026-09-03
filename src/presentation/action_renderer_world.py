"""World, entity and HUD drawing for Action Run."""

from __future__ import annotations

from typing import Any

import pygame

from src.domain import ActionRunPhase, Faction, GridPos, PreparedActionKind
from src.presentation.action_art import (
    draw_enemy_weapon,
    draw_floor_tile,
    draw_hazard_tile,
    draw_player_actor,
    draw_wall_tile,
)
from src.presentation.action_assets import draw_meowa_unit
from src.presentation.action_renderer_values import (
    ACTION_TUTORIAL_REPLAY_RECT, CELL_SIZE, COLORS, GRID_ORIGIN,
    INTENT_LABELS, NEW_RUN_RECT, PANEL_X, SHOWCASE_RECT, WINDOW_SIZE,
)


class ActionWorldMixin:
    def _menu(self, app: Any) -> None:
        self._center("ACTION ROGUELIKE // TACTICAL CAUSALITY", 14, COLORS["muted"], (640, 78), True, "data")
        pygame.draw.circle(self.screen, COLORS["cyan_dark"], (640, 242), 112, 3)
        pygame.draw.circle(self.screen, COLORS["violet"], (640, 242), 78, 2)
        self._diamond((640, 242), 58, COLORS["cyan"], 4)
        self._center("ECHO // ZERO", 56, COLORS["text"], (640, 388), True, "display")
        self._center("动作 Roguelike + 战术因果编排", 22, COLORS["cyan"], (640, 440), True)
        self._center("实时交锋  ·  冻结战局  ·  改写因果", 16, COLORS["muted"], (640, 478))
        self._button(NEW_RUN_RECT, "NEW RUN  //  开始远征  [ENTER]", True)
        self._button(SHOWCASE_RECT, "TUTORIAL  //  教学演示  [F5]", False)
        unlock = "VETERAN FRAME  //  老兵框架 · CORE +1" if app.meta.veteran_frame_unlocked else "VETERAN FRAME  //  老兵框架 · 完成一局后解锁"
        self._center(unlock, 12, COLORS["success"] if app.meta.veteran_frame_unlocked else COLORS["muted"], (640, 710), False, "data")

    def _run(self, app: Any) -> None:
        run = app.run_state
        phase = run.phase
        self._text_at("ECHO // ZERO", 28, COLORS["text"], (48, 38), True, "display")
        self._text_at(
            f"PROCEDURAL RUN   SEED {run.seed}",
            14,
            COLORS["cyan"],
            (48, 82),
            True,
            "data",
        )
        encounter_label = (
            "FINAL ENCOUNTER  ·  BOSS SIGNAL"
            if run.encounter_index + 1 == run.ENCOUNTER_COUNT
            else f"ENCOUNTER {run.encounter_index + 1}/{run.ENCOUNTER_COUNT}"
        )
        self._text_at(
            f"{encounter_label}   ·   GENERATION ATTEMPT {run.map.generation_attempt + 1}",
            13,
            COLORS["muted"],
            (48, 108),
            False,
            "data",
        )
        self._map(app)
        self._hud(app)
        if phase is ActionRunPhase.ACTION and run.encounter_elapsed < run.ENCOUNTER_GRACE:
            remaining = max(0.0, run.ENCOUNTER_GRACE - run.encounter_elapsed)
            banner = pygame.Rect(278, 148, 364, 48)
            self._panel(banner, (29, 58, 70), COLORS["cyan"], 2, 8, COLORS["cyan"])
            self._center(
                f"同步窗口  {remaining:0.1f} 秒  ·  先移动观察，Q 可冻结",
                14,
                COLORS["text"],
                banner.center,
                True,
                "data",
            )
        if app.core_flash_until > pygame.time.get_ticks():
            feedback = pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)
            pygame.draw.rect(feedback, (*COLORS["danger"], 55), pygame.Rect(0, 0, WINDOW_SIZE[0], WINDOW_SIZE[1]), 18)
            self.screen.blit(feedback, (0, 0))
        if phase is ActionRunPhase.TACTICAL:
            self._tactical(app)
        elif phase is ActionRunPhase.REWARD:
            self._reward(app)
        elif phase in {ActionRunPhase.VICTORY, ActionRunPhase.DEFEAT}:
            self._result(app)
        now = pygame.time.get_ticks()
        if not app.keyboard_focused:
            banner = pygame.Rect(218, 654, 484, 48)
            pygame.draw.rect(self.screen, (55, 42, 28), banner, border_radius=5)
            pygame.draw.rect(self.screen, COLORS["warning"], banner, 2, border_radius=5)
            self._center("键盘未激活 · 点击游戏窗口继续", 15, COLORS["text"], banner.center, True)
        elif app.input_notice_until > now:
            banner = pygame.Rect(344, 654, 232, 38)
            pygame.draw.rect(self.screen, COLORS["surface_high"], banner, border_radius=4)
            pygame.draw.rect(self.screen, COLORS["cyan"], banner, 2, border_radius=4)
            self._center(app.input_notice, 14, COLORS["text"], banner.center, True)

    def _map(self, app: Any) -> None:
        run = app.run_state
        now = pygame.time.get_ticks()
        board = pygame.Rect(
            GRID_ORIGIN[0] - 8,
            GRID_ORIGIN[1] - 8,
            run.map.width * CELL_SIZE + 16,
            run.map.height * CELL_SIZE + 16,
        )
        self._panel(board, (18, 31, 43), COLORS["border"], 2, 8, COLORS["cyan_dark"])
        for y in range(run.map.height):
            for x in range(run.map.width):
                pos = GridPos(x, y)
                rect = self.cell_rect(pos)
                if pos in run.map.floor:
                    draw_floor_tile(
                        self.screen,
                        rect,
                        COLORS["floor_a"],
                        COLORS["floor_b"],
                        COLORS["floor_line"],
                        x + y * 3,
                    )
                else:
                    draw_wall_tile(
                        self.screen, rect, COLORS["wall"], COLORS["wall_edge"]
                    )
        for pos in run.map.hazards:
            draw_hazard_tile(
                self.screen,
                self.cell_rect(pos),
                COLORS["danger"],
                COLORS["warning"],
                0.0 if app.reduced_motion else now / 1000,
            )
        reward_rect = self.cell_rect(run.map.reward_pos).inflate(-12, -12)
        self._diamond(reward_rect.center, 15, COLORS["success"], 2)
        pygame.draw.circle(self.screen, COLORS["success"], reward_rect.center, 5, 1)
        self._center("NODE", 9, COLORS["success"], (reward_rect.centerx, reward_rect.bottom + 5), True, "data")

        preview = run.preview
        if preview is not None:
            for entity in preview.state.entities.values():
                rect = self.cell_rect(entity.pos).inflate(-12, -12)
                ghost_color = COLORS["cyan"] if entity.faction is Faction.PLAYER else COLORS["danger"]
                pygame.draw.rect(self.screen, ghost_color, rect, 2, border_radius=4)
                ghost_label = "P" if entity.faction is Faction.PLAYER else f"E{run.enemy_number(entity.entity_id)}"
                self._center(ghost_label, 10, ghost_color, rect.center, True, "data")
                source = run.state.entities.get(entity.entity_id)
                if source is not None and source.pos != entity.pos:
                    self._arrow(self.cell_rect(source.pos).center, rect.center, ghost_color, 1)

        for enemy in run.active_enemies:
            prepared = run.prepared_actions.get(enemy.entity_id)
            if prepared is not None:
                start = self.cell_rect(enemy.pos).center
                end = self.cell_rect(prepared.target_pos).center
                pygame.draw.line(self.screen, (255, 174, 180), start, end, 3)
                targets = prepared.target_positions or (prepared.target_pos,)
                for target in targets:
                    target_center = self.cell_rect(target).center
                    pygame.draw.circle(self.screen, COLORS["danger"], target_center, 17 if len(targets) > 1 else 11, 3)
                    pygame.draw.circle(self.screen, COLORS["text"], target_center, 3)
        for entity in run.state.entities.values():
            self._entity(app, entity)
        for enemy in run.active_enemies:
            if enemy.entity_id not in run.state.entities:
                continue
            rect = self.cell_rect(enemy.pos)
            badge_center = (rect.left + 12, rect.top + 12)
            pygame.draw.circle(self.screen, COLORS["background"], badge_center, 11)
            pygame.draw.circle(self.screen, COLORS["danger"], badge_center, 11, 2)
            self._center(f"E{run.enemy_number(enemy.entity_id)}", 9, COLORS["text"], badge_center, True, "data")
        if app.dodge_trail is not None and app.dodge_trail[2] > now:
            start = self.cell_rect(app.dodge_trail[0]).center
            end = self.cell_rect(app.dodge_trail[1]).center
            pygame.draw.line(self.screen, COLORS["cyan"], start, end, 8)
            pygame.draw.circle(self.screen, COLORS["text"], start, 9, 2)
        for origin, destination, until in app.move_trails:
            if until > now:
                alpha = max(0.15, min(0.65, (until - now) / 150))
                trail = pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)
                start = self.cell_rect(origin).center
                end = self.cell_rect(destination).center
                pygame.draw.line(trail, (*COLORS["cyan"], round(120 * alpha)), start, end, 4)
                pygame.draw.circle(trail, (*COLORS["cyan"], round(80 * alpha)), start, 13, 2)
                self.screen.blit(trail, (0, 0))
        for position, until in app.hit_marks:
            if until > now:
                center = self.cell_rect(position).center
                pygame.draw.circle(self.screen, COLORS["text"], center, 19, 3)
                pygame.draw.line(self.screen, COLORS["warning"], (center[0] - 20, center[1]), (center[0] + 20, center[1]), 2)
                pygame.draw.line(self.screen, COLORS["warning"], (center[0], center[1] - 20), (center[0], center[1] + 20), 2)
        for origin, destination, until in app.shot_trails:
            if until > now:
                start = self.cell_rect(origin).center
                end = self.cell_rect(destination).center
                pygame.draw.line(self.screen, COLORS["warning"], start, end, 5)
                pygame.draw.line(self.screen, COLORS["text"], start, end, 1)
                pygame.draw.circle(self.screen, COLORS["warning"], end, 6, 2)
        for position, until in app.death_fragments:
            if until > now:
                self._death_dissolve(position, until, now)
        warden = next((enemy for enemy in run.active_enemies if enemy.enemy_kind == "warden"), None)
        if warden is not None:
            bar = pygame.Rect(184, 714, 560, 16)
            self._panel(bar.inflate(10, 18), COLORS["surface"], COLORS["border"], 2, 6, COLORS["danger"])
            pygame.draw.rect(self.screen, (38, 29, 22), bar)
            fill = bar.copy()
            fill.width = round(bar.width * warden.hp / warden.max_hp)
            pygame.draw.rect(self.screen, COLORS["danger"], fill)
            phase_text = "过载加速" if warden.hp <= warden.max_hp // 2 else "十字爆发"
            self._center(
                f"相位守卫  {warden.hp}/{warden.max_hp}  ·  {phase_text}",
                12, COLORS["text"], bar.center, True, "data",
            )

    def _entity(self, app: Any, entity: Any) -> None:
        rect = self.cell_rect(entity.pos).inflate(-6, -6)
        flash = app.flash_until.get(entity.entity_id, 0) > pygame.time.get_ticks()
        if entity.faction is Faction.PLAYER:
            now = pygame.time.get_ticks()
            pose, progress = app.player_pose_frame(now)
            facing = app.run_state.facing.delta
            animation = pose if pose in {"idle", "move", "attack", "dodge", "hurt"} else "attack"
            sprite = self.sprites.get(
                "player",
                facing,
                flash=flash,
                animation=animation,
                progress=0.0 if app.reduced_motion else progress,
            )
            if sprite is None:
                draw_player_actor(
                    self.screen,
                    rect.center,
                    20,
                    pose,
                    facing,
                    progress,
                    COLORS["cyan"],
                    COLORS["text"],
                    flash,
                )
            else:
                dx, dy = facing
                impulse = 4 if pose in {"attack", "dodge"} else 0
                bob = 1 if pose == "move" and progress > 0.5 else 0
                draw_meowa_unit(
                    self.screen,
                    sprite,
                    (rect.centerx + dx * impulse, rect.centery + dy * impulse - bob),
                    size=50,
                    accent=COLORS["cyan"],
                )
                breath = 0 if app.reduced_motion else (now // 280) % 2
                pygame.draw.circle(self.screen, COLORS["cyan_dark"], rect.center, 23 + breath, 1)
                self._diamond(rect.center, 4, COLORS["cyan"], 0)
            if pose == "attack":
                start = rect.center
                dx, dy = app.run_state.facing.delta
                end = (start[0] + dx * 34, start[1] + dy * 34)
                pygame.draw.line(self.screen, COLORS["text"], start, end, 2)
        else:
            color = {
                "melee": COLORS["danger"],
                "charger": COLORS["warning"],
                "ranged": COLORS["violet"],
                "warden": COLORS["success"],
            }.get(entity.enemy_kind, COLORS["danger"])
            prepared = app.run_state.prepared_actions.get(entity.entity_id)
            facing = (0, 1)
            if prepared is not None:
                delta_x = prepared.target_pos.x - entity.pos.x
                delta_y = prepared.target_pos.y - entity.pos.y
                facing = (
                    (1 if delta_x > 0 else -1, 0)
                    if abs(delta_x) >= abs(delta_y) and delta_x != 0
                    else (0, 1 if delta_y > 0 else -1)
                )
            remaining = max(0.0, app.run_state.enemy_timers.get(entity.entity_id, 0.0))
            animation = "prepared" if prepared is not None and remaining < 0.45 else "idle"
            animation_progress = (
                0.0
                if app.reduced_motion
                else ((1.0 - remaining / 0.45) if animation == "prepared" else (pygame.time.get_ticks() % 560) / 560)
            )
            sprite = self.sprites.get(
                entity.enemy_kind or "melee",
                facing,
                flash=flash,
                animation=animation,
                progress=animation_progress,
            )
            if sprite is None:
                draw_unit_icon(
                    self.screen,
                    rect.center,
                    20,
                    entity.enemy_kind or "melee",
                    color,
                    COLORS["text"],
                    flash,
                )
            else:
                draw_meowa_unit(
                    self.screen,
                    sprite,
                    rect.center,
                    size=50 if entity.enemy_kind != "warden" else 54,
                    accent=color,
                    elite=app.run_state.encounter_index > 0 or entity.enemy_kind == "warden",
                )
            if prepared is not None:
                target = self.cell_rect(prepared.target_pos).center
                if remaining < 0.45:
                    pulse = 24 + round((1.0 - remaining / 0.45) * 6)
                    pygame.draw.circle(self.screen, color, rect.center, pulse, 2)
                draw_enemy_weapon(
                    self.screen,
                    rect.center,
                    target,
                    entity.enemy_kind or "melee",
                    color,
                    pygame.time.get_ticks() / 1000,
                    prepared.kind in {PreparedActionKind.ATTACK, PreparedActionKind.SPECIAL},
                )
        bar = pygame.Rect(rect.x + 1, rect.bottom + 2, rect.width - 2, 6)
        pygame.draw.rect(self.screen, (49, 31, 42), bar)
        if entity.hp > 0:
            fill = bar.copy()
            fill.width = round(bar.width * entity.hp / entity.max_hp)
            pygame.draw.rect(self.screen, COLORS["success"] if entity.faction is Faction.PLAYER else COLORS["danger"], fill)

    def _hud(self, app: Any) -> None:
        run = app.run_state
        player = run.player
        panel = pygame.Rect(PANEL_X - 16, 32, 324, 710)
        self._panel(panel, COLORS["surface"], COLORS["border"], 2, 12, COLORS["cyan"])
        pygame.draw.rect(self.screen, COLORS["cyan"], pygame.Rect(panel.x, 66, 3, 116))
        pygame.draw.rect(self.screen, COLORS["violet"], pygame.Rect(panel.x, 478, 3, 178))
        self._text_at("实时战斗", 15, COLORS["cyan"], (PANEL_X, 48), True)
        self._text_at("ACTION COMBAT", 10, COLORS["muted"], (PANEL_X + 194, 53), True, "data")
        hp = f"{player.hp}/{player.max_hp}" if player is not None else "0/0"
        shield = player.shield if player is not None else 0
        core_color = COLORS["danger"] if app.core_flash_until > pygame.time.get_ticks() else COLORS["text"]
        self._text_at("核心 / 护盾", 11, COLORS["muted"], (PANEL_X, 78), True)
        self._text_at(f"{hp}   /   {shield}", 22, core_color, (PANEL_X, 96), True, "data")
        self._meter("闪避", run.dodge_cooldown, run.dodge_cooldown_base, (PANEL_X, 140))
        self._meter("牵引技能", run.skill_cooldown, 2.2, (PANEL_X, 170))
        self._meter("战术模式 [Q]", run.tactical_cooldown, run.TACTICAL_COOLDOWN, (PANEL_X, 200))
        mode_ranged = run.attack_mode.value == "ranged"
        mode_color = COLORS["warning"] if mode_ranged else COLORS["success"]
        mode_label = "远程 · 3格 · 半伤" if mode_ranged else "近战 · 1格 · 全伤"
        mode_rect = pygame.Rect(PANEL_X, 228, 290, 30)
        self._panel(mode_rect, COLORS["surface_high"], mode_color, 2, 5, mode_color)
        self._text_at(f"C  攻击模式：{mode_label}", 12, COLORS["text"], (PANEL_X + 14, 236), True)
        self._text_at("SPACE 攻击  ·  SHIFT+方向键 闪避", 11, COLORS["muted"], (PANEL_X, 266))
        self._text_at("E 牵引  ·  Q 战术模式", 11, COLORS["muted"], (PANEL_X, 284))
        pygame.draw.line(self.screen, COLORS["border"], (PANEL_X, 310), (PANEL_X + 290, 310), 1)
        self._text_at("敌方意图", 13, COLORS["danger"], (PANEL_X, 320), True)
        self._text_at("ENEMY INTENT", 9, COLORS["muted"], (PANEL_X + 190, 325), True, "data")
        y = 346
        for enemy in run.active_enemies[:4]:
            action = run.prepared_actions.get(enemy.entity_id)
            label = self._intent_label(action.label if action is not None else "")
            timer = max(0.0, run.enemy_timers.get(enemy.entity_id, 0.0))
            self._panel(pygame.Rect(PANEL_X, y, 290, 26), (39, 48, 64), COLORS["border"], 1, 4, COLORS["danger"])
            self._text_at(f"{timer:0.1f}s", 11, COLORS["danger"], (PANEL_X + 8, y + 6), True, "data")
            self._text_at(f"E{run.enemy_number(enemy.entity_id)}  {enemy.display_name}  →  {label}", 12, COLORS["text"], (PANEL_X + 56, y + 5), True)
            y += 31
        pygame.draw.line(self.screen, COLORS["border"], (PANEL_X, 486), (PANEL_X + 290, 486), 1)
        self._text_at("本局构筑", 13, COLORS["violet"], (PANEL_X, 498), True)
        self._text_at("BUILD", 9, COLORS["muted"], (PANEL_X + 244, 503), True, "data")
        self._build_panel(run, pygame.Rect(PANEL_X, 528, 290, 130))
        if run.phase is ActionRunPhase.ACTION:
            self._button(ACTION_TUTORIAL_REPLAY_RECT, "重新进入教学", False)
