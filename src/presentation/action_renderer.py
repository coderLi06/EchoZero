"""Read-only pygame presentation for the procedural action run."""

from __future__ import annotations

from typing import Any

import pygame

from src.domain import (
    ActionRunPhase,
    CommandType,
    Faction,
    GridPos,
    PreparedActionKind,
    RewardKind,
)
from src.presentation.action_art import (
    draw_enemy_weapon,
    draw_floor_tile,
    draw_hazard_tile,
    draw_player_actor,
    draw_unit_icon,
    draw_wall_tile,
)

WINDOW_SIZE = (1280, 800)
CELL_SIZE = 56
GRID_ORIGIN = (40, 136)
PANEL_X = 916
NEW_RUN_RECT = pygame.Rect(440, 530, 400, 66)
SHOWCASE_RECT = pygame.Rect(440, 612, 400, 54)
REWARD_RECTS = tuple(pygame.Rect(50 + index * 410, 270, 360, 300) for index in range(3))
TACTICAL_SLOT_RECTS = tuple(
    pygame.Rect(PANEL_X, 424 + index * 62, 308, 52) for index in range(3)
)
TACTICAL_EXECUTE_RECT = pygame.Rect(PANEL_X, 618, 190, 58)
TACTICAL_CANCEL_RECT = pygame.Rect(PANEL_X + 200, 618, 108, 58)
ACTION_TUTORIAL_REPLAY_RECT = pygame.Rect(PANEL_X + 88, 682, 220, 48)
ACTION_TUTORIAL_BACK_RECT = pygame.Rect(804, 656, 120, 48)
ACTION_TUTORIAL_SKIP_STEP_RECT = pygame.Rect(936, 656, 132, 48)
ACTION_TUTORIAL_SKIP_ALL_RECT = pygame.Rect(1080, 656, 140, 48)

TUTORIAL_BOARD_RECT = pygame.Rect(40, 132, 840, 476)
TUTORIAL_CORE_RECT = pygame.Rect(PANEL_X, 84, 308, 58)
TUTORIAL_MOVEMENT_RECT = pygame.Rect(PANEL_X, 158, 308, 42)
TUTORIAL_ACTION_RECT = pygame.Rect(PANEL_X, 208, 308, 68)
TUTORIAL_INTENT_RECT = pygame.Rect(PANEL_X, 294, 308, 82)
TUTORIAL_TACTICAL_RECT = pygame.Rect(PANEL_X, 388, 308, 46)
TUTORIAL_TIMELINE_RECT = pygame.Rect(PANEL_X, 440, 308, 102)
TUTORIAL_REWARD_RECT = pygame.Rect(PANEL_X, 548, 308, 62)

COLORS = {
    "background": (11, 20, 31),
    "surface": (24, 38, 53),
    "surface_high": (35, 54, 72),
    "border": (86, 116, 140),
    "text": (249, 252, 255),
    "muted": (197, 214, 228),
    "cyan": (78, 226, 255),
    "cyan_dark": (24, 91, 113),
    "violet": (198, 153, 255),
    "danger": (255, 104, 112),
    "warning": (255, 202, 92),
    "success": (92, 235, 173),
    "floor_a": (38, 64, 83),
    "floor_b": (43, 71, 91),
    "floor_line": (61, 93, 116),
    "wall": (15, 25, 35),
    "wall_edge": (43, 59, 73),
    "hazard": (126, 47, 53),
}
REWARD_KIND_LABELS = {
    RewardKind.PROTOCOL: "协议",
    RewardKind.SKILL: "技能",
    RewardKind.STAT: "属性",
}
REWARD_KIND_COLORS = {
    RewardKind.PROTOCOL: COLORS["violet"],
    RewardKind.SKILL: COLORS["cyan"],
    RewardKind.STAT: COLORS["success"],
}
INTENT_LABELS = {
    "CHASE": "追击",
    "STRIKE": "近身攻击",
    "SHOOT": "瞄准射击",
    "CHARGE": "准备突袭",
    "PHASE BURST": "相位爆发",
    "KEEP RANGE": "拉开距离",
    "STRAFE": "侧向机动",
    "REPOSITION": "重新部署",
}
TIMELINE_LABELS = {
    "stable": "稳定",
    "reverse": "逆相",
}
DIRECTION_LABELS = {
    "UP": "上",
    "RIGHT": "右",
    "DOWN": "下",
    "LEFT": "左",
}
PROTOCOL_EFFECT_LABELS = {
    "repeat_first_on_empty_third": "第 3 拍为空时，重放第 1 拍",
    "push_damage_plus_one": "推击伤害 +1",
    "pull_range_plus_one": "牵引距离 +1 格",
    "shield_plus_one": "护盾命令额外 +1 层",
    "echo_grants_shield": "回声触发时获得 1 层护盾",
    "collision_damage_plus_one": "撞墙伤害 +1",
    "pull_cancels_intent": "牵引成功时取消敌方意图",
    "shield_primes_push": "先护盾后推击，伤害 +1",
}


class ActionRenderer:
    def __init__(self, output: pygame.Surface) -> None:
        self.output = output
        self.screen = pygame.Surface(WINDOW_SIZE)
        self.viewport = pygame.Rect((0, 0), WINDOW_SIZE)
        self.fonts: dict[tuple[int, bool, str], pygame.font.Font] = {}
        self.text_cache: dict[tuple[str, int, tuple[int, int, int], bool, str], pygame.Surface] = {}
        self.update_viewport_layout(output)

    def update_viewport_layout(self, output: pygame.Surface | None = None) -> None:
        if output is not None:
            self.output = output
        width, height = self.output.get_size()
        if width <= 0 or height <= 0:
            self.viewport = pygame.Rect(0, 0, 0, 0)
            return
        scale = min(width / WINDOW_SIZE[0], height / WINDOW_SIZE[1])
        size = (max(1, round(WINDOW_SIZE[0] * scale)), max(1, round(WINDOW_SIZE[1] * scale)))
        self.viewport = pygame.Rect((width - size[0]) // 2, (height - size[1]) // 2, *size)

    def to_logical(self, pos: tuple[int, int]) -> tuple[int, int] | None:
        if not self.viewport.collidepoint(pos):
            return None
        return (
            round((pos[0] - self.viewport.x) * WINDOW_SIZE[0] / self.viewport.width),
            round((pos[1] - self.viewport.y) * WINDOW_SIZE[1] / self.viewport.height),
        )

    def grid_pos(self, logical: tuple[int, int]) -> GridPos:
        return GridPos(
            (logical[0] - GRID_ORIGIN[0]) // CELL_SIZE,
            (logical[1] - GRID_ORIGIN[1]) // CELL_SIZE,
        )

    def draw(self, app: Any) -> None:
        self.screen.fill(COLORS["background"])
        for x in range(0, WINDOW_SIZE[0], 64):
            pygame.draw.line(self.screen, (19, 32, 45), (x, 0), (x, WINDOW_SIZE[1]))
        for y in range(0, WINDOW_SIZE[1], 64):
            pygame.draw.line(self.screen, (19, 32, 45), (0, y), (WINDOW_SIZE[0], y))
        pygame.draw.line(self.screen, COLORS["cyan"], (0, 0), (WINDOW_SIZE[0], 0), 3)
        if app.tutorial.active:
            self._tutorial(app)
        elif app.run_state is None:
            self._menu(app)
        else:
            self._run(app)
        self._text_at("ESC 退出   ·   F2 减弱动态   ·   F3 技术面板", 12, COLORS["muted"], (48, 776))
        if app.run_state is not None and app.debug_panel:
            self._debug_panel(app)
        if app.reward_acquisition_active:
            self._reward_acquired(app)
        self.output.fill(COLORS["background"])
        scaled = (
            self.screen
            if self.viewport.size == WINDOW_SIZE
            else pygame.transform.smoothscale(self.screen, self.viewport.size)
        )
        self.output.blit(scaled, self.viewport)

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
            pygame.draw.rect(self.screen, (29, 58, 70), banner, border_radius=8)
            pygame.draw.rect(self.screen, COLORS["cyan"], banner, 2, border_radius=8)
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
        pygame.draw.rect(self.screen, (18, 31, 43), board, border_radius=10)
        pygame.draw.rect(self.screen, COLORS["border"], board, 2, border_radius=10)
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
                self._center("P" if entity.faction is Faction.PLAYER else "E", 11, ghost_color, rect.center, True, "data")
                source = run.state.entities.get(entity.entity_id)
                if source is not None and source.pos != entity.pos:
                    self._arrow(self.cell_rect(source.pos).center, rect.center, ghost_color, 1)

        for enemy in run.active_enemies:
            prepared = run.prepared_actions.get(enemy.entity_id)
            if prepared is not None:
                start = self.cell_rect(enemy.pos).center
                end = self.cell_rect(prepared.target_pos).center
                pygame.draw.line(self.screen, (255, 174, 180), start, end, 3)
                pygame.draw.circle(self.screen, COLORS["danger"], end, 11, 3)
                pygame.draw.circle(self.screen, COLORS["text"], end, 3)
        for entity in run.state.entities.values():
            self._entity(app, entity)
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
        for position, until in app.death_fragments:
            if until > now:
                self._death_dissolve(position, until, now)

    def _entity(self, app: Any, entity: Any) -> None:
        rect = self.cell_rect(entity.pos).inflate(-6, -6)
        flash = app.flash_until.get(entity.entity_id, 0) > pygame.time.get_ticks()
        if entity.faction is Faction.PLAYER:
            now = pygame.time.get_ticks()
            pose, progress = app.player_pose_frame(now)
            draw_player_actor(
                self.screen,
                rect.center,
                20,
                pose,
                app.run_state.facing.delta,
                progress,
                COLORS["cyan"],
                COLORS["text"],
                flash,
            )
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
            draw_unit_icon(
                self.screen,
                rect.center,
                20,
                entity.enemy_kind or "melee",
                color,
                COLORS["text"],
                flash,
            )
            prepared = app.run_state.prepared_actions.get(entity.entity_id)
            if prepared is not None:
                target = self.cell_rect(prepared.target_pos).center
                remaining = max(0.0, app.run_state.enemy_timers.get(entity.entity_id, 0.0))
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
        pygame.draw.rect(self.screen, COLORS["surface"], panel, border_radius=6)
        pygame.draw.rect(self.screen, COLORS["border"], panel, 2, border_radius=6)
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
        self._text_at("WASD / 方向键 移动  ·  SPACE 攻击", 12, COLORS["text"], (PANEL_X, 236))
        self._text_at("SHIFT+方向键 闪避  ·  E 牵引  ·  Q 战术", 11, COLORS["muted"], (PANEL_X, 258))
        pygame.draw.line(self.screen, COLORS["border"], (PANEL_X, 286), (PANEL_X + 290, 286), 1)
        self._text_at("敌方意图", 13, COLORS["danger"], (PANEL_X, 304), True)
        self._text_at("ENEMY INTENT", 9, COLORS["muted"], (PANEL_X + 190, 309), True, "data")
        y = 332
        for enemy in run.active_enemies[:4]:
            action = run.prepared_actions.get(enemy.entity_id)
            label = self._intent_label(action.label if action is not None else "")
            timer = max(0.0, run.enemy_timers.get(enemy.entity_id, 0.0))
            pygame.draw.rect(self.screen, (39, 48, 64), pygame.Rect(PANEL_X, y, 290, 26), border_radius=3)
            self._text_at(f"{timer:0.1f}s", 11, COLORS["danger"], (PANEL_X + 8, y + 6), True, "data")
            self._text_at(f"{enemy.display_name}  →  {label}", 12, COLORS["text"], (PANEL_X + 56, y + 5), True)
            y += 31
        pygame.draw.line(self.screen, COLORS["border"], (PANEL_X, 468), (PANEL_X + 290, 468), 1)
        self._text_at("本局构筑", 13, COLORS["violet"], (PANEL_X, 486), True)
        self._text_at("BUILD", 9, COLORS["muted"], (PANEL_X + 244, 491), True, "data")
        self._build_panel(run, pygame.Rect(PANEL_X, 516, 290, 142))
        if run.phase is ActionRunPhase.ACTION:
            self._button(ACTION_TUTORIAL_REPLAY_RECT, "重新进入教学", False)

    def _tutorial(self, app: Any) -> None:
        step = app.tutorial.current
        if step is None:
            return
        self._text_at("ECHO // ZERO", 28, COLORS["text"], (48, 38), True, "display")
        self._text_at("TRAINING SIMULATION // NO SEED CONSUMED", 14, COLORS["warning"], (48, 84), True, "data")
        self._text_at("教学期间正式敌人计时暂停；高亮区域就是当前要看的内容。", 14, COLORS["text"], (48, 108))
        self._tutorial_mock_board()
        self._tutorial_mock_hud()
        self._tutorial_mock_rewards()

        targets = self._tutorial_target_rects(step.target)
        shade = pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)
        shade.fill((3, 8, 14, 145))
        for rect in targets:
            shade.fill((0, 0, 0, 0), rect.inflate(12, 12))
        self.screen.blit(shade, (0, 0))
        for rect in targets:
            pygame.draw.rect(
                self.screen,
                COLORS["warning"],
                rect.inflate(8, 8),
                4,
                border_radius=10,
            )

        panel = pygame.Rect(48, 632, 1184, 120)
        pygame.draw.rect(self.screen, COLORS["surface"], panel, border_radius=12)
        pygame.draw.rect(self.screen, COLORS["warning"], panel, 3, border_radius=12)
        current, total = app.tutorial.progress
        self._text_at(
            f"TRAINING  {current}/{total}",
            13,
            COLORS["warning"],
            (66, 682),
            True,
            "data",
        )
        self._text_at(step.title, 22, COLORS["text"], (66, 646), True, "display")
        self._wrapped(
            step.body,
            16,
            COLORS["text"],
            pygame.Rect(190, 680, 574, 52),
            22,
        )
        self._button(ACTION_TUTORIAL_BACK_RECT, "上一步", False)
        self._button(ACTION_TUTORIAL_SKIP_STEP_RECT, "跳过本步", True)
        self._button(ACTION_TUTORIAL_SKIP_ALL_RECT, "全部跳过", False)
        self._text_at("TAB / ENTER 继续   SHIFT+TAB 返回   F1 全部跳过   ESC 退出教学", 11, COLORS["muted"], (804, 716), False, "data")

    def _tutorial_mock_board(self) -> None:
        pygame.draw.rect(self.screen, COLORS["surface"], TUTORIAL_BOARD_RECT, border_radius=10)
        for y in range(7):
            for x in range(13):
                rect = pygame.Rect(52 + x * 62, 144 + y * 62, 62, 62)
                draw_floor_tile(
                    self.screen,
                    rect,
                    COLORS["floor_a"],
                    COLORS["floor_b"],
                    COLORS["floor_line"],
                    x + y * 3,
                )
        hazard_rect = pygame.Rect(52 + 3 * 62, 144 + 4 * 62, 62, 62)
        draw_hazard_tile(
            self.screen, hazard_rect, COLORS["danger"], COLORS["warning"]
        )
        player = (52 + 7 * 62 + 31, 144 + 3 * 62 + 31)
        enemy = (52 + 10 * 62 + 31, 144 + 3 * 62 + 31)
        draw_unit_icon(self.screen, player, 23, "player", COLORS["cyan"], COLORS["background"])
        draw_unit_icon(self.screen, enemy, 21, "melee", COLORS["danger"], COLORS["text"])
        pygame.draw.line(self.screen, COLORS["danger"], enemy, player, 3)
        pygame.draw.circle(self.screen, COLORS["danger"], player, 28, 3)
        self._text_at("WASD", 14, COLORS["cyan"], (player[0] - 25, player[1] + 30), True, "data")

    def _tutorial_mock_hud(self) -> None:
        panel = pygame.Rect(PANEL_X - 16, 56, 324, 564)
        pygame.draw.rect(self.screen, COLORS["surface"], panel, border_radius=12)
        pygame.draw.rect(self.screen, COLORS["border"], panel, 2, border_radius=12)
        self._text_at("实时战斗", 14, COLORS["cyan"], (PANEL_X, 68), True)
        self._text_at("核心 8/8 · 护盾 0", 19, COLORS["text"], (PANEL_X, 100), True)
        self._text_at("WASD  实时移动", 15, COLORS["text"], (PANEL_X, 176), True)
        self._text_at("SPACE  攻击并击退", 14, COLORS["text"], (PANEL_X, 222))
        self._text_at("SHIFT+WASD 闪避 · E 牵引", 13, COLORS["text"], (PANEL_X, 252))
        self._text_at("敌方意图", 12, COLORS["danger"], (PANEL_X, 314), True)
        self._text_at("追猎体  →  追击", 15, COLORS["text"], (PANEL_X, 344), True)
        self._text_at("Q  战术模式", 13, COLORS["violet"], (PANEL_X, 412), True)
        labels = ("1  位移", "2  推击", "3  空拍")
        for index, label in enumerate(labels):
            rect = pygame.Rect(PANEL_X, 450 + index * 36, 308, 32)
            pygame.draw.rect(self.screen, COLORS["surface_high"], rect, border_radius=7)
            pygame.draw.rect(self.screen, COLORS["cyan"] if index == 0 else COLORS["border"], rect, 2, border_radius=7)
            self._text_at(label, 12, COLORS["text"], (rect.x + 10, rect.y + 8), True)
        self._text_at("预演 · 核心 8 · 敌人 1", 11, COLORS["cyan"], (PANEL_X, 562), True)

    def _tutorial_mock_rewards(self) -> None:
        pygame.draw.rect(self.screen, COLORS["surface_high"], TUTORIAL_REWARD_RECT, border_radius=10)
        labels = (
            ("协议", COLORS["violet"]),
            ("技能", COLORS["cyan"]),
            ("属性", COLORS["success"]),
        )
        for index, (label, color) in enumerate(labels):
            rect = pygame.Rect(PANEL_X + 6 + index * 98, 554, 92, 50)
            pygame.draw.rect(self.screen, COLORS["surface_high"], rect, border_radius=8)
            pygame.draw.rect(self.screen, color, rect, 2, border_radius=8)
            self._center(label, 10, color, rect.center, True, "data")

    @staticmethod
    def _tutorial_target_rects(target: str) -> tuple[pygame.Rect, ...]:
        mapping = {
            "board": (TUTORIAL_BOARD_RECT,),
            "core": (TUTORIAL_CORE_RECT,),
            "movement": (TUTORIAL_BOARD_RECT, TUTORIAL_MOVEMENT_RECT),
            "action_controls": (TUTORIAL_ACTION_RECT,),
            "intent": (TUTORIAL_INTENT_RECT, TUTORIAL_BOARD_RECT),
            "tactical": (TUTORIAL_TACTICAL_RECT,),
            "timeline": (TUTORIAL_TIMELINE_RECT,),
            "rewards": (TUTORIAL_REWARD_RECT,),
            "ready": (TUTORIAL_BOARD_RECT, TUTORIAL_TACTICAL_RECT),
        }
        return mapping.get(target, (TUTORIAL_BOARD_RECT,))

    def _tactical(self, app: Any) -> None:
        run = app.run_state
        overlay = pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)
        overlay.fill((5, 16, 27, 148))
        if not app.reduced_motion:
            scan_y = 132 + (pygame.time.get_ticks() // 7) % 570
            pygame.draw.line(overlay, (78, 226, 255, 26), (32, scan_y), (882, scan_y), 1)
        self.screen.blit(overlay, (0, 0))
        pygame.draw.rect(self.screen, COLORS["cyan"], pygame.Rect(18, 18, 864, 704), 2)
        for hazard in run.map.hazards:
            rect = self.cell_rect(hazard).inflate(-7, -7)
            pygame.draw.rect(self.screen, COLORS["danger"], rect, 1)
            for offset in range(-rect.height, rect.width, 12):
                pygame.draw.line(
                    self.screen,
                    (177, 61, 73),
                    (rect.x + max(0, offset), rect.bottom - max(0, -offset)),
                    (rect.x + min(rect.width, offset + rect.height), rect.bottom - min(rect.height, rect.width - offset)),
                    1,
                )
        panel = pygame.Rect(PANEL_X - 16, 290, 324, 430)
        pygame.draw.rect(self.screen, (19, 29, 48), panel, border_radius=6)
        pygame.draw.rect(self.screen, COLORS["cyan"], panel, 3, border_radius=6)
        self._text_at("战术模式", 17, COLORS["cyan"], (PANEL_X, 308), True)
        self._text_at("时间冻结 · 敌方意图已锁定", 12, COLORS["muted"], (PANEL_X, 334), True)
        self._text_at(
            f"时间线：{TIMELINE_LABELS.get(run.state.active_timeline_rule.value, run.state.active_timeline_rule.value)}  ·  编辑三拍",
            13,
            COLORS["muted"],
            (PANEL_X, 358),
        )
        preview = run.preview
        if preview is not None:
            player = preview.state.entities.get("player")
            hp = player.hp if player is not None else 0
            self._text_at(
                f"预演结果  核心 {hp}  ·  敌人 {sum(e.faction is Faction.ENEMY for e in preview.state.entities.values())}",
                15,
                COLORS["cyan"],
                (PANEL_X, 390),
                True,
                "data",
            )
        labels = {
            CommandType.WAIT: "空拍",
            CommandType.MOVE: "位移",
            CommandType.PUSH: "推击",
            CommandType.PULL: "牵引",
            CommandType.SHIELD: "护盾",
        }
        for index, rect in enumerate(TACTICAL_SLOT_RECTS):
            selected = app.selected_slot == index
            pygame.draw.rect(self.screen, COLORS["surface_high"], rect, border_radius=8)
            pygame.draw.rect(self.screen, COLORS["cyan"] if selected else COLORS["border"], rect, 3 if selected else 1, border_radius=8)
            command = run.commands[index]
            detail = DIRECTION_LABELS.get(command.direction.name, command.direction.name) if command.direction is not None else command.target_entity_id or ""
            self._text_at(f"{index + 1}  {labels[command.command_type]}  {detail}", 15, COLORS["text"], (rect.x + 14, rect.y + 15), True)
        self._button(TACTICAL_EXECUTE_RECT, "执行  [ENTER]", True)
        self._button(TACTICAL_CANCEL_RECT, "返回 [Q]", False)
        self._text_at("1/2/3 选拍 · WASD 位移 · SPACE 推击", 10, COLORS["text"], (PANEL_X, 682))
        self._text_at("E 牵引 · F 护盾 · BACKSPACE 空拍", 10, COLORS["text"], (PANEL_X, 696))

    def _reward(self, app: Any) -> None:
        run = app.run_state
        shade = pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)
        shade.fill((4, 9, 16, 195))
        self.screen.blit(shade, (0, 0))
        self._center("选择强化", 30, COLORS["text"], (640, 138), True, "display")
        self._center("SELECT UPGRADE", 12, COLORS["muted"], (640, 178), True, "data")
        self._center(f"种子 {run.seed}  ·  选择后写入本局构筑", 13, COLORS["muted"], (640, 210), False)
        logical_mouse = self.to_logical(pygame.mouse.get_pos())
        for index, (choice, rect) in enumerate(zip(run.reward_choices, REWARD_RECTS)):
            hovered = logical_mouse is not None and rect.collidepoint(logical_mouse)
            focused = index == app.reward_focus or hovered
            draw_rect = rect.inflate(6, 6) if hovered and not app.reduced_motion else rect
            color = REWARD_KIND_COLORS[choice.kind]
            kind_label = REWARD_KIND_LABELS[choice.kind]
            pygame.draw.rect(self.screen, COLORS["surface"], draw_rect, border_radius=6)
            pygame.draw.rect(self.screen, color if focused else COLORS["border"], draw_rect, 4 if focused else 2, border_radius=6)
            self._reward_glyph(choice.kind, (draw_rect.centerx, draw_rect.y + 36), color)
            self._center(kind_label, 12, color, (draw_rect.centerx, draw_rect.y + 70), True, "data")
            self._center(choice.display_name, 23, COLORS["text"], (draw_rect.centerx, draw_rect.y + 112), True)
            self._text_at("核心效果", 11, COLORS["muted"], (draw_rect.x + 24, draw_rect.y + 148), True)
            self._wrapped(choice.description, 15, COLORS["text"], pygame.Rect(draw_rect.x + 24, draw_rect.y + 172, draw_rect.width - 48, 58), 22, True)
            note = {
                RewardKind.PROTOCOL: "改写三拍规则",
                RewardKind.SKILL: "强化动作回路",
                RewardKind.STAT: "提升核心参数",
            }[choice.kind]
            self._center(note, 12, COLORS["muted"], (draw_rect.centerx, draw_rect.bottom - 46), False)
            self._center(f"[{index + 1}]  选择", 13, color, (draw_rect.centerx, draw_rect.bottom - 22), True)

    def _result(self, app: Any) -> None:
        run = app.run_state
        victory = run.phase is ActionRunPhase.VICTORY
        shade = pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)
        shade.fill((4, 9, 16, 205))
        self.screen.blit(shade, (0, 0))
        self._center("远征完成" if victory else "信号中断", 52, COLORS["success"] if victory else COLORS["danger"], (640, 272), True, "display")
        self._center(f"种子 {run.seed}  ·  遭遇 {run.encounter_index + 1}/{run.ENCOUNTER_COUNT}", 17, COLORS["muted"], (640, 340), True)
        self._center(run.build_summary, 18, COLORS["violet"], (640, 386))
        if app.unlock_just_earned:
            self._center("局外解锁 // 老兵框架：下一局起始核心 +1", 17, COLORS["warning"], (640, 438), True)
        self._button(NEW_RUN_RECT, "NEW RUN  //  再次远征  [ENTER]", True)
        self._center("死亡与通关都会保留少量局外解锁；地图、敌人与奖励重新生成。", 14, COLORS["muted"], (640, 632))

    def _build_panel(self, run: Any, rect: pygame.Rect) -> None:
        entries: list[tuple[str, str, str, tuple[int, int, int]]] = []
        for protocol_id, stacks in run.build.items():
            if stacks <= 0 or protocol_id not in run.plugins:
                continue
            protocol = run.plugins[protocol_id]
            name = protocol.display_name
            suffix = f" ×{stacks}" if stacks > 1 else ""
            effect = PROTOCOL_EFFECT_LABELS.get(
                protocol.effect_type, protocol.description.split("。", 1)[0]
            )
            entries.append(("协议", f"{name}{suffix}", effect, COLORS["violet"]))
        if run.attack_cooldown_base < 0.34:
            percent = round((1 - run.attack_cooldown_base / 0.34) * 100)
            entries.append(("技能", "脉冲加速", f"基础攻击冷却 -{percent}%", COLORS["cyan"]))
        if run.dodge_cooldown_base < 1.35:
            entries.append(("技能", "闪避回路", f"闪避冷却 -{1.35 - run.dodge_cooldown_base:0.2f} 秒", COLORS["cyan"]))
        if run.skill_damage > 1:
            entries.append(("技能", "牵引增幅", f"牵引脉冲伤害 +{run.skill_damage - 1}", COLORS["cyan"]))
        if run.attack_damage > 1:
            entries.append(("属性", "锋刃校准", f"基础攻击伤害 +{run.attack_damage - 1}", COLORS["success"]))
        if run.max_core_bonus > 0:
            entries.append(("属性", "核心扩容", f"最大核心 +{run.max_core_bonus}", COLORS["success"]))
        if not entries:
            pygame.draw.rect(self.screen, (31, 43, 59), rect, border_radius=4)
            pygame.draw.rect(self.screen, COLORS["border"], rect, 1, border_radius=4)
            self._text_at("暂无强化", 15, COLORS["text"], (rect.x + 14, rect.y + 18), True)
            self._text_at("完成遭遇后可选择一项强化", 12, COLORS["muted"], (rect.x + 14, rect.y + 48))
            return
        counts = {
            "协议": sum(kind == "协议" for kind, _, _, _ in entries),
            "技能": sum(kind == "技能" for kind, _, _, _ in entries),
            "属性": sum(kind == "属性" for kind, _, _, _ in entries),
        }
        self._text_at(f"已选强化  {len(entries):02d}", 10, COLORS["muted"], (rect.x, rect.y), True)
        for index in range(min(6, len(entries))):
            pip = pygame.Rect(rect.x + 192 + index * 16, rect.y + 2, 10, 6)
            pygame.draw.rect(self.screen, COLORS["violet"], pip)
        for index, (kind, name, effect, color) in enumerate(entries[:2]):
            row = pygame.Rect(rect.x, rect.y + 22 + index * 50, rect.width, 45)
            pygame.draw.rect(self.screen, (31, 43, 59), row, border_radius=3)
            pygame.draw.line(self.screen, color, row.topleft, row.bottomleft, 3)
            self._text_at(kind, 10, color, (row.x + 10, row.y + 8), True)
            self._text_at(name, 12, COLORS["text"], (row.x + 54, row.y + 5), True)
            self._text_at(effect, 10, COLORS["muted"], (row.x + 54, row.y + 25))
        self._text_at(
            f"协议 {counts['协议']}  ·  技能 {counts['技能']}  ·  属性 {counts['属性']}",
            9,
            COLORS["muted"],
            (rect.x, rect.bottom - 10),
            True,
            "data",
        )

    def _debug_panel(self, app: Any) -> None:
        run = app.run_state
        if run is None:
            return
        shade = pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)
        shade.fill((3, 8, 14, 96))
        self.screen.blit(shade, (0, 0))
        panel = pygame.Rect(66, 150, 520, 430)
        pygame.draw.rect(self.screen, (15, 25, 37), panel, border_radius=4)
        pygame.draw.rect(self.screen, COLORS["warning"], panel, 2, border_radius=4)
        self._text_at("TECHNICAL VIEW  [F3]", 17, COLORS["warning"], (88, 172), True, "data")
        self._text_at("答辩模式 · 正式 HUD 默认关闭", 13, COLORS["muted"], (88, 202))
        pygame.draw.line(self.screen, COLORS["border"], (88, 232), (564, 232), 1)
        nodes = ("Selector", "Sequence", "Condition", "PreparedAction")
        for index, node in enumerate(nodes):
            x = 90 + index * 116
            box = pygame.Rect(x, 252, 104, 34)
            pygame.draw.rect(self.screen, COLORS["surface_high"], box, border_radius=3)
            pygame.draw.rect(self.screen, COLORS["cyan"] if index == 3 else COLORS["border"], box, 1, border_radius=3)
            self._center(node, 10, COLORS["text"], box.center, True, "data")
            if index < len(nodes) - 1:
                pygame.draw.line(self.screen, COLORS["border"], (box.right, box.centery), (box.right + 12, box.centery), 1)
        self._text_at("LIVE PREPARED ACTIONS", 11, COLORS["danger"], (88, 318), True, "data")
        y = 348
        for enemy in run.active_enemies[:5]:
            action = run.prepared_actions.get(enemy.entity_id)
            if action is None:
                continue
            self._text_at(enemy.display_name, 13, COLORS["text"], (88, y), True)
            self._text_at(action.kind.value.upper(), 11, COLORS["danger"], (230, y + 2), True, "data")
            self._text_at(f"PreparedAction → {action.label}", 11, COLORS["muted"], (342, y + 2), False, "data")
            y += 34
        self._text_at("Intent 与实时执行读取同一个 PreparedAction", 12, COLORS["cyan"], (88, 532), True)

    def _reward_acquired(self, app: Any) -> None:
        reward = app.reward_acquisition
        if reward is None:
            return
        shade = pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)
        shade.fill((4, 9, 16, 210))
        self.screen.blit(shade, (0, 0))
        color = REWARD_KIND_COLORS[reward.kind]
        panel = pygame.Rect(380, 242, 520, 300)
        pygame.draw.rect(self.screen, COLORS["surface"], panel, border_radius=6)
        pygame.draw.rect(self.screen, color, panel, 3, border_radius=6)
        self._reward_glyph(reward.kind, (panel.centerx, panel.y + 58), color)
        self._center("获得强化", 19, color, (panel.centerx, panel.y + 110), True)
        self._center(reward.display_name, 28, COLORS["text"], (panel.centerx, panel.y + 184), True, "display")
        self._center(reward.description, 14, COLORS["text"], (panel.centerx, panel.y + 228))
        self._center("已写入本局构筑 · 短暂反馈后自动恢复操作", 11, COLORS["muted"], (panel.centerx, panel.y + 270), True)

    def _death_dissolve(self, position: GridPos, until: int, now: int) -> None:
        center = self.cell_rect(position).center
        progress = 1.0 - max(0.0, min(1.0, (until - now) / 460))
        color = COLORS["danger"]
        for index in range(6):
            y = center[1] - 18 + index * 7 - round(progress * (index % 2) * 8)
            half = max(2, 19 - round(progress * 14) - index)
            pygame.draw.line(self.screen, color, (center[0] - half, y), (center[0] + half, y), 2)
        for dx, dy in ((-22, -12), (19, -7), (-15, 18), (23, 15)):
            pygame.draw.rect(self.screen, color, pygame.Rect(center[0] + dx, center[1] + dy - round(progress * 18), 3, 3))

    def _reward_glyph(self, kind: RewardKind, center: tuple[int, int], color: tuple[int, int, int]) -> None:
        if kind is RewardKind.PROTOCOL:
            self._diamond(center, 14, color, 2)
            pygame.draw.circle(self.screen, color, center, 4, 1)
        elif kind is RewardKind.SKILL:
            pygame.draw.arc(self.screen, color, pygame.Rect(center[0] - 15, center[1] - 15, 30, 30), 0.2, 4.8, 3)
            pygame.draw.line(self.screen, color, (center[0] - 2, center[1] - 4), (center[0] + 11, center[1] - 12), 3)
        else:
            pygame.draw.line(self.screen, color, (center[0] - 15, center[1]), (center[0] + 15, center[1]), 3)
            pygame.draw.line(self.screen, color, (center[0], center[1] - 15), (center[0], center[1] + 15), 3)

    def _arrow(self, start: tuple[int, int], end: tuple[int, int], color: tuple[int, int, int], width: int = 2) -> None:
        pygame.draw.line(self.screen, color, start, end, width)
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = max(1.0, (dx * dx + dy * dy) ** 0.5)
        ux, uy = dx / length, dy / length
        left = (round(end[0] - ux * 10 - uy * 5), round(end[1] - uy * 10 + ux * 5))
        right = (round(end[0] - ux * 10 + uy * 5), round(end[1] - uy * 10 - ux * 5))
        pygame.draw.polygon(self.screen, color, (end, left, right))

    @staticmethod
    def _intent_label(label: str) -> str:
        return INTENT_LABELS.get(label, "观察战局" if not label else label)

    def _meter(self, label: str, remaining: float, maximum: float, pos: tuple[int, int]) -> None:
        self._text_at(label, 11, COLORS["muted"], pos, True, "data")
        rect = pygame.Rect(pos[0] + 94, pos[1] + 2, 196, 10)
        pygame.draw.rect(self.screen, (43, 54, 72), rect, border_radius=5)
        ready = maximum <= 0 or remaining <= 0
        fill = rect.copy()
        fill.width = rect.width if ready else round(rect.width * (1 - min(1.0, remaining / maximum)))
        pygame.draw.rect(self.screen, COLORS["success"] if ready else COLORS["cyan"], fill, border_radius=5)

    @staticmethod
    def cell_rect(pos: GridPos) -> pygame.Rect:
        return pygame.Rect(
            GRID_ORIGIN[0] + pos.x * CELL_SIZE,
            GRID_ORIGIN[1] + pos.y * CELL_SIZE,
            CELL_SIZE,
            CELL_SIZE,
        )

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

    def _button(self, rect: pygame.Rect, label: str, primary: bool) -> None:
        pygame.draw.rect(self.screen, COLORS["cyan_dark"] if primary else COLORS["surface_high"], rect, border_radius=4)
        pygame.draw.rect(self.screen, COLORS["cyan"] if primary else COLORS["border"], rect, 3 if primary else 2, border_radius=4)
        self._center(label, 17, COLORS["text"], rect.center, True, "data")

    def _diamond(self, center: tuple[int, int], radius: int, color: tuple[int, int, int], width: int) -> None:
        pygame.draw.polygon(
            self.screen,
            color,
            [
                (center[0], center[1] - radius),
                (center[0] + radius, center[1]),
                (center[0], center[1] + radius),
                (center[0] - radius, center[1]),
            ],
            width,
        )
