"""Tactical, reward, result and diagnostic overlays for Action Run."""

from __future__ import annotations

from typing import Any

import pygame

from src.domain import ActionRunPhase, CommandType, Faction, GridPos, RewardKind
from src.presentation.action_renderer_values import (
    COLORS, DIRECTION_LABELS, NEW_RUN_RECT, PANEL_X, PROTOCOL_EFFECT_LABELS,
    REWARD_KIND_COLORS, REWARD_KIND_LABELS, REWARD_RECTS, TACTICAL_ACTION_RECTS,
    TACTICAL_CANCEL_RECT, TACTICAL_DOWN_RECT, TACTICAL_EXECUTE_RECT,
    TACTICAL_UP_RECT, TIMELINE_LABELS, WINDOW_SIZE,
)


class ActionOverlayMixin:
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
        panel = pygame.Rect(PANEL_X - 16, 62, 324, 680)
        self._panel(panel, (19, 29, 48), COLORS["cyan"], 3, 12, COLORS["cyan"])
        pygame.draw.rect(self.screen, COLORS["cyan"], pygame.Rect(panel.x, panel.y + 18, 3, 108))
        self._text_at("战术模式 · 动作优先队列", 17, COLORS["cyan"], (PANEL_X, 80), True)
        self._text_at("时间冻结 · 前三项实际执行", 12, COLORS["muted"], (PANEL_X, 106), True)
        chain_label, chain_color = self._tactical_chain(run.commands)
        chain_name = chain_label.split(" ·", 1)[0]
        self._text_at(
            f"时间线：{TIMELINE_LABELS.get(run.state.active_timeline_rule.value, run.state.active_timeline_rule.value)}  ·  因果链：{chain_name}",
            12,
            chain_color,
            (PANEL_X, 132),
        )
        summary = run.tactical_preview_summary
        if summary is not None:
            self._text_at("预演战损", 13, COLORS["cyan"], (PANEL_X, 162), True)
            player_rect = pygame.Rect(PANEL_X, 184, 308, 30)
            self._panel(player_rect, COLORS["surface_high"], COLORS["success"], 1, 5, COLORS["success"])
            player_delta = summary.player_before_hp - summary.player_after_hp
            player_result = f"HP {summary.player_before_hp} → {summary.player_after_hp}"
            if player_delta > 0:
                player_result += f"  (-{player_delta})"
            self._text_at("玩家", 11, COLORS["text"], (player_rect.x + 12, player_rect.y + 8), True)
            self._text_at(player_result, 11, COLORS["text"], (player_rect.x + 102, player_rect.y + 8), True, "data")
            if summary.enemy_deltas:
                for row, delta in enumerate(summary.enemy_deltas[:3]):
                    rect = pygame.Rect(PANEL_X, 218 + row * 28, 308, 26)
                    self._panel(rect, COLORS["surface"], COLORS["danger"], 1, 4, COLORS["danger"])
                    self._text_at(
                        f"E{delta.number}  {delta.display_name}", 10, COLORS["text"],
                        (rect.x + 10, rect.y + 6), True,
                    )
                    self._text_at(
                        f"HP {delta.before_hp} → {delta.after_hp}  (-{delta.damage})",
                        10, COLORS["danger"], (rect.x + 158, rect.y + 6), True, "data",
                    )
            else:
                self._text_at("前三拍未对敌人造成伤害", 10, COLORS["muted"], (PANEL_X + 10, 225))
        labels = {
            CommandType.WAIT: "空拍",
            CommandType.MOVE: "位移",
            CommandType.PUSH: "推击",
            CommandType.PULL: "牵引",
            CommandType.SHIELD: "护盾",
        }
        self._text_at("调整前三拍后，战损即时刷新", 10, COLORS["muted"], (PANEL_X, 304))
        for index, (action, rect) in enumerate(zip(run.tactical_actions, TACTICAL_ACTION_RECTS)):
            selected = app.selected_slot == index
            executes = index < 3
            self._panel(
                rect,
                COLORS["surface_high"] if executes else COLORS["surface"],
                COLORS["cyan"] if selected else COLORS["border"],
                3 if selected else 1,
                7,
                COLORS["cyan"] if selected else None,
            )
            command = action.command
            detail = DIRECTION_LABELS.get(command.direction.name, command.direction.name) if command.direction is not None else command.target_entity_id or ""
            badge = f"{index + 1} · 拍{index + 1}" if executes else f"{index + 1} · 候补"
            badge_color = COLORS["cyan"] if executes else COLORS["muted"]
            self._text_at(badge, 10, badge_color, (rect.x + 10, rect.y + 7), True)
            self._text_at(action.display_name, 13, COLORS["text"], (rect.x + 58, rect.y + 5), True)
            self._text_at(f"{labels[command.command_type]}  {detail}", 9, COLORS["muted"], (rect.x + 58, rect.y + 27))
        self._button(TACTICAL_UP_RECT, "↑", False)
        self._button(TACTICAL_DOWN_RECT, "↓", False)
        self._button(TACTICAL_EXECUTE_RECT, "执行 [ENTER]", True)
        self._button(TACTICAL_CANCEL_RECT, "Q 返回", False)

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
            self._panel(
                draw_rect,
                COLORS["surface"],
                color if focused else COLORS["border"],
                4 if focused else 2,
                14,
                color,
            )
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
        self._panel(
            pygame.Rect(352, 214, 576, 432),
            COLORS["surface"],
            COLORS["success"] if victory else COLORS["danger"],
            2,
            18,
            COLORS["success"] if victory else COLORS["danger"],
        )
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
            self._panel(rect, (31, 43, 59), COLORS["border"], 1, 7, COLORS["violet"])
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
            self._panel(row, (31, 43, 59), COLORS["border"], 1, 5, color)
            pygame.draw.line(self.screen, color, (row.x, row.y + 5), (row.x, row.bottom - 5), 3)
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
        self._panel(panel, (15, 25, 37), COLORS["warning"], 2, 10, COLORS["warning"])
        self._text_at("TECHNICAL VIEW  [F3]", 17, COLORS["warning"], (88, 172), True, "data")
        self._text_at("答辩模式 · 正式 HUD 默认关闭", 13, COLORS["muted"], (88, 202))
        pygame.draw.line(self.screen, COLORS["border"], (88, 232), (564, 232), 1)
        nodes = ("Selector", "Sequence", "Condition", "PreparedAction")
        for index, node in enumerate(nodes):
            x = 90 + index * 116
            box = pygame.Rect(x, 252, 104, 34)
            self._panel(
                box,
                COLORS["surface_high"],
                COLORS["cyan"] if index == 3 else COLORS["border"],
                1,
                4,
                COLORS["cyan"] if index == 3 else None,
            )
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
        self._panel(panel, COLORS["surface"], color, 3, 16, color)
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
