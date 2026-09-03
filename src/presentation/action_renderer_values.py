"""Shared layout constants for Action Run rendering."""

from __future__ import annotations

import pygame

from src.domain import RewardKind

WINDOW_SIZE = (1280, 800)
CELL_SIZE = 56
GRID_ORIGIN = (40, 136)
PANEL_X = 916
NEW_RUN_RECT = pygame.Rect(440, 530, 400, 66)
SHOWCASE_RECT = pygame.Rect(440, 612, 400, 54)
REWARD_RECTS = tuple(pygame.Rect(50 + index * 410, 270, 360, 300) for index in range(3))
TACTICAL_ACTION_RECTS = tuple(
    pygame.Rect(PANEL_X, 320 + index * 50, 308, 48) for index in range(7)
)
TACTICAL_SLOT_RECTS = TACTICAL_ACTION_RECTS[:3]
TACTICAL_UP_RECT = pygame.Rect(PANEL_X, 682, 48, 48)
TACTICAL_DOWN_RECT = pygame.Rect(PANEL_X + 56, 682, 48, 48)
TACTICAL_EXECUTE_RECT = pygame.Rect(PANEL_X + 112, 682, 124, 48)
TACTICAL_CANCEL_RECT = pygame.Rect(PANEL_X + 244, 682, 64, 48)
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
TUTORIAL_TIMELINE_RECT = pygame.Rect(PANEL_X, 438, 308, 158)
TUTORIAL_REWARD_RECT = pygame.Rect(PANEL_X, 548, 308, 62)

COLORS = {
    "background": (20, 18, 14),
    "surface": (42, 39, 31),
    "surface_high": (61, 55, 42),
    "border": (132, 114, 78),
    "text": (232, 222, 185),
    "muted": (174, 163, 128),
    "cyan": (215, 171, 82),
    "cyan_dark": (91, 75, 42),
    "violet": (177, 112, 68),
    "danger": (201, 78, 57),
    "warning": (231, 188, 84),
    "success": (143, 162, 91),
    "floor_a": (55, 53, 42),
    "floor_b": (62, 59, 46),
    "floor_line": (83, 77, 57),
    "wall": (27, 25, 21),
    "wall_edge": (76, 67, 48),
    "hazard": (119, 52, 40),
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
    "PHASE CROSS": "十字相位爆发",
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
