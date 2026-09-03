"""Independent tutorial rendering for Action Run."""

from __future__ import annotations

from typing import Any

import pygame

from src.presentation.action_art import draw_floor_tile, draw_hazard_tile, draw_unit_icon
from src.presentation.action_renderer_values import (
    ACTION_TUTORIAL_BACK_RECT, ACTION_TUTORIAL_SKIP_ALL_RECT,
    ACTION_TUTORIAL_SKIP_STEP_RECT, COLORS, PANEL_X,
    TUTORIAL_ACTION_RECT, TUTORIAL_BOARD_RECT, TUTORIAL_CORE_RECT,
    TUTORIAL_INTENT_RECT, TUTORIAL_MOVEMENT_RECT, TUTORIAL_REWARD_RECT,
    TUTORIAL_TACTICAL_RECT, TUTORIAL_TIMELINE_RECT, WINDOW_SIZE,
)


class ActionTutorialMixin:
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
        self._panel(panel, COLORS["surface"], COLORS["warning"], 3, 14, COLORS["warning"])
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
        self._panel(TUTORIAL_BOARD_RECT, COLORS["surface"], COLORS["border"], 1, 10, COLORS["warning"])
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
        self._panel(panel, COLORS["surface"], COLORS["border"], 2, 12, COLORS["warning"])
        self._text_at("实时战斗", 14, COLORS["cyan"], (PANEL_X, 68), True)
        self._text_at("核心 8/8 · 护盾 0", 19, COLORS["text"], (PANEL_X, 100), True)
        self._text_at("WASD  实时移动", 15, COLORS["text"], (PANEL_X, 176), True)
        self._text_at("C  近战 ↔ 远程（3格 / 半伤）", 14, COLORS["warning"], (PANEL_X, 214), True)
        self._text_at("SPACE  朝面对方向攻击", 13, COLORS["text"], (PANEL_X, 240))
        self._text_at("SHIFT+WASD 闪避 · E 牵引", 12, COLORS["text"], (PANEL_X, 264))
        self._text_at("敌方意图", 12, COLORS["danger"], (PANEL_X, 314), True)
        self._text_at("追猎体  →  追击", 15, COLORS["text"], (PANEL_X, 344), True)
        self._text_at("Q  战术模式", 13, COLORS["violet"], (PANEL_X, 412), True)
        labels = ("拍1  正面推击", "拍2  牵引目标", "拍3  展开护盾", "候补  向前位移")
        for index, label in enumerate(labels):
            rect = pygame.Rect(PANEL_X, 444 + index * 30, 308, 27)
            self._panel(
                rect,
                COLORS["surface_high"],
                COLORS["cyan"] if index == 0 else COLORS["border"],
                2,
                5,
                COLORS["cyan"] if index == 0 else None,
            )
            self._text_at(label, 11, COLORS["text"], (rect.x + 10, rect.y + 6), True)
        self._text_at("另有 3 条候补 · W/S 调整", 10, COLORS["muted"], (PANEL_X, 568), True)
        self._text_at("预演 · 核心 8 · 敌人 1", 11, COLORS["cyan"], (PANEL_X, 590), True)

    def _tutorial_mock_rewards(self) -> None:
        self._panel(TUTORIAL_REWARD_RECT, COLORS["surface_high"], COLORS["border"], 1, 8, COLORS["warning"])
        labels = (
            ("协议", COLORS["violet"]),
            ("技能", COLORS["cyan"]),
            ("属性", COLORS["success"]),
        )
        for index, (label, color) in enumerate(labels):
            rect = pygame.Rect(PANEL_X + 6 + index * 98, 554, 92, 50)
            self._panel(rect, COLORS["surface_high"], color, 2, 6, color)
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
