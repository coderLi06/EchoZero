"""Read-only pygame presentation coordinator for the procedural action run."""

from __future__ import annotations

from typing import Any

import pygame

from src.domain import CommandType, GridPos
from src.presentation.action_assets import ActionSpriteLibrary
from src.presentation.fonts import load_ui_font, text_font_role
from src.presentation.action_renderer_overlays import ActionOverlayMixin
from src.presentation.action_renderer_tutorial import ActionTutorialMixin
from src.presentation.action_renderer_values import (
    ACTION_TUTORIAL_BACK_RECT, ACTION_TUTORIAL_REPLAY_RECT,
    ACTION_TUTORIAL_SKIP_ALL_RECT, ACTION_TUTORIAL_SKIP_STEP_RECT,
    CELL_SIZE, COLORS, GRID_ORIGIN, INTENT_LABELS, NEW_RUN_RECT, PANEL_X,
    REWARD_KIND_LABELS, REWARD_RECTS, SHOWCASE_RECT, TACTICAL_ACTION_RECTS,
    TACTICAL_CANCEL_RECT, TACTICAL_DOWN_RECT, TACTICAL_EXECUTE_RECT,
    TACTICAL_SLOT_RECTS, TACTICAL_UP_RECT, WINDOW_SIZE,
)
from src.presentation.action_renderer_world import ActionWorldMixin


class ActionRenderer(ActionWorldMixin, ActionTutorialMixin, ActionOverlayMixin):
    def __init__(self, output: pygame.Surface) -> None:
        self.output = output
        self.screen = pygame.Surface(WINDOW_SIZE)
        self.viewport = pygame.Rect((0, 0), WINDOW_SIZE)
        self.fonts: dict[tuple[int, bool, str], pygame.font.Font] = {}
        self.text_cache: dict[tuple[str, int, tuple[int, int, int], bool, str], pygame.Surface] = {}
        self.sprites = ActionSpriteLibrary()
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
            pygame.draw.line(self.screen, (34, 31, 24), (x, 0), (x, WINDOW_SIZE[1]))
        for y in range(0, WINDOW_SIZE[1], 64):
            pygame.draw.line(self.screen, (34, 31, 24), (0, y), (WINDOW_SIZE[0], y))
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
        pygame.draw.rect(self.screen, COLORS["surface_high"], rect)
        ready = maximum <= 0 or remaining <= 0
        fill = rect.copy()
        fill.width = rect.width if ready else round(rect.width * (1 - min(1.0, remaining / maximum)))
        pygame.draw.rect(self.screen, COLORS["success"] if ready else COLORS["cyan"], fill)
        pygame.draw.line(self.screen, COLORS["background"], (rect.centerx, rect.y), (rect.centerx, rect.bottom), 1)

    @staticmethod
    def _tactical_chain(commands: list[Any]) -> tuple[str, tuple[int, int, int]]:
        kinds = tuple(command.command_type for command in commands)
        if kinds == (CommandType.PULL, CommandType.PUSH, CommandType.MOVE):
            return ("锁断 · 拉近 → 击退 → 脱离", COLORS["violet"])
        if kinds[:2] == (CommandType.SHIELD, CommandType.PUSH):
            return ("盾势 · 先防御后反推", COLORS["success"])
        if kinds[0] is not CommandType.WAIT and kinds[0] is kinds[2]:
            return ("回声 · 首尾命令呼应", COLORS["violet"])
        if all(kind is CommandType.WAIT for kind in kinds):
            return ("未编排 · 选择三拍观察预演", COLORS["muted"])
        return ("已编排 · 调整顺序比较结果", COLORS["cyan"])

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
            self.fonts[key] = load_ui_font(size, bold, role)
        return self.fonts[key]

    def _surface(self, text: str, size: int, color: tuple[int, int, int], bold: bool = False, role: str = "body") -> pygame.Surface:
        key = (text, size, color, bold, role)
        if key not in self.text_cache:
            effective_role = text_font_role(text, role)
            self.text_cache[key] = self._font(size, bold, effective_role).render(text, True, color)
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
        self._panel(
            rect,
            COLORS["cyan_dark"] if primary else COLORS["surface_high"],
            COLORS["cyan"] if primary else COLORS["border"],
            3 if primary else 2,
            10,
            COLORS["cyan"] if primary else None,
        )
        self._center(label, 17, COLORS["text"], rect.center, True, "data")

    def _panel(
        self,
        rect: pygame.Rect,
        fill: tuple[int, int, int],
        border: tuple[int, int, int],
        width: int = 2,
        cut: int = 10,
        accent: tuple[int, int, int] | None = None,
    ) -> None:
        cut = max(0, min(cut, rect.width // 4, rect.height // 4))
        points = (
            (rect.x + cut, rect.y),
            (rect.right - cut, rect.y),
            (rect.right, rect.y + cut),
            (rect.right, rect.bottom - cut),
            (rect.right - cut, rect.bottom),
            (rect.x + cut, rect.bottom),
            (rect.x, rect.bottom - cut),
            (rect.x, rect.y + cut),
        )
        pygame.draw.polygon(self.screen, fill, points)
        if width > 0:
            pygame.draw.polygon(self.screen, border, points, width)
        if accent is not None and rect.width >= 56:
            pygame.draw.line(
                self.screen,
                accent,
                (rect.x + cut + 4, rect.y + 1),
                (min(rect.right - cut - 4, rect.x + cut + 34), rect.y + 1),
                2,
            )
            pygame.draw.line(
                self.screen,
                accent,
                (rect.right - cut - 4, rect.bottom - 1),
                (max(rect.x + cut + 4, rect.right - cut - 24), rect.bottom - 1),
                2,
            )
        if rect.width >= 100 and rect.height >= 42:
            inner = rect.inflate(-8, -8)
            pygame.draw.rect(self.screen, (24, 22, 18), inner, 1, border_radius=3)
            pygame.draw.line(
                self.screen, (175, 150, 96),
                (rect.x + cut + 5, rect.y + 3),
                (rect.right - cut - 5, rect.y + 3), 1,
            )
            pygame.draw.line(
                self.screen, (18, 16, 13),
                (rect.x + cut + 5, rect.bottom - 4),
                (rect.right - cut - 5, rect.bottom - 4), 2,
            )
            for center in (
                (rect.x + 10, rect.y + 10),
                (rect.right - 11, rect.y + 10),
                (rect.x + 10, rect.bottom - 11),
                (rect.right - 11, rect.bottom - 11),
            ):
                pygame.draw.circle(self.screen, (24, 22, 18), center, 3)
                pygame.draw.circle(self.screen, COLORS["border"], center, 3, 1)

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
