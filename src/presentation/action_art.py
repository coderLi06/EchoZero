"""Code-native visual language for EchoZero action encounters."""

from __future__ import annotations

import pygame


def _polygon_points(
    center: tuple[int, int], offsets: tuple[tuple[int, int], ...]
) -> list[tuple[int, int]]:
    return [(center[0] + dx, center[1] + dy) for dx, dy in offsets]


def draw_floor_tile(
    surface: pygame.Surface,
    rect: pygame.Rect,
    primary: tuple[int, int, int],
    secondary: tuple[int, int, int],
    circuit: tuple[int, int, int],
    variant: int,
) -> None:
    pygame.draw.rect(surface, primary if variant % 2 == 0 else secondary, rect)
    inset = rect.inflate(-4, -4)
    pygame.draw.rect(surface, circuit, inset, 1, border_radius=4)
    pygame.draw.circle(surface, circuit, (inset.x + 6, inset.y + 6), 1)
    pygame.draw.line(surface, circuit, (inset.right - 10, inset.bottom - 4), (inset.right - 4, inset.bottom - 10), 1)
    if variant % 3 == 0:
        pygame.draw.line(surface, circuit, (inset.x + 7, inset.centery), (inset.right - 7, inset.centery), 1)
        pygame.draw.circle(surface, circuit, inset.center, 2)
    elif variant % 3 == 1:
        pygame.draw.line(surface, circuit, (inset.centerx, inset.y + 7), (inset.centerx, inset.bottom - 7), 1)
        pygame.draw.circle(surface, circuit, inset.center, 2)


def draw_wall_tile(
    surface: pygame.Surface,
    rect: pygame.Rect,
    base: tuple[int, int, int],
    edge: tuple[int, int, int],
) -> None:
    pygame.draw.rect(surface, base, rect)
    pygame.draw.line(surface, edge, rect.topleft, rect.topright, 2)
    pygame.draw.line(surface, edge, rect.topleft, rect.bottomleft, 1)
    pygame.draw.line(surface, (12, 22, 31), rect.bottomleft, rect.bottomright, 3)
    bolt = max(1, rect.width // 24)
    for point in ((rect.x + 8, rect.y + 8), (rect.right - 8, rect.bottom - 8)):
        pygame.draw.circle(surface, edge, point, bolt)


def draw_hazard_tile(
    surface: pygame.Surface,
    rect: pygame.Rect,
    danger: tuple[int, int, int],
    warning: tuple[int, int, int],
    phase: float = 0.0,
) -> None:
    inner = rect.inflate(-8, -8)
    pygame.draw.rect(surface, (71, 35, 42), inner, border_radius=4)
    pygame.draw.rect(surface, danger, inner, 2, border_radius=4)
    for offset in range(-inner.height, inner.width, 10):
        start = (inner.x + max(0, offset), inner.bottom - max(0, -offset))
        end = (inner.x + min(inner.width, offset + inner.height), inner.bottom - min(inner.height, inner.width - offset))
        pygame.draw.line(surface, (122, 54, 63), start, end, 1)
    flame_base = inner.bottom - 6
    for index, offset in enumerate((-13, 0, 13)):
        flicker = ((int(phase * 9) + index * 2) % 5) - 2
        height = 25 + (index % 2) * 7 + flicker
        center_x = inner.centerx + offset
        flame = (
            (center_x, flame_base - height),
            (center_x + 8, flame_base - 12),
            (center_x + 6, flame_base),
            (center_x - 7, flame_base),
            (center_x - 9, flame_base - 12),
        )
        pygame.draw.polygon(surface, danger, flame)
        pygame.draw.polygon(
            surface,
            warning,
            ((center_x, flame_base - height // 2), (center_x + 4, flame_base - 5), (center_x - 4, flame_base - 5)),
        )


def draw_unit_icon(
    surface: pygame.Surface,
    center: tuple[int, int],
    radius: int,
    kind: str,
    color: tuple[int, int, int],
    ink: tuple[int, int, int],
    flash: bool = False,
) -> None:
    if flash:
        color = (255, 255, 255)
    shadow = (7, 16, 24)
    if kind == "player":
        draw_player_actor(surface, center, radius, "idle", (1, 0), 0.0, color, ink, flash)
    elif kind == "charger":
        body = _polygon_points(center, ((radius, 0), (-radius + 3, -radius + 3), (-radius // 2, 0), (-radius + 3, radius - 3)))
        pygame.draw.polygon(surface, shadow, body)
        pygame.draw.polygon(surface, color, body, 4)
        pygame.draw.line(surface, color, (center[0] - radius, center[1] - 8), (center[0] - radius - 8, center[1] - 8), 4)
        pygame.draw.line(surface, color, (center[0] - radius, center[1] + 8), (center[0] - radius - 8, center[1] + 8), 4)
    elif kind == "ranged":
        pygame.draw.circle(surface, shadow, center, radius)
        pygame.draw.circle(surface, color, center, radius, 4)
        pygame.draw.circle(surface, color, center, max(4, radius // 3), 2)
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            start = (center[0] + dx * (radius - 3), center[1] + dy * (radius - 3))
            end = (center[0] + dx * (radius + 7), center[1] + dy * (radius + 7))
            pygame.draw.line(surface, color, start, end, 3)
        pygame.draw.circle(surface, ink, center, 3)
    elif kind == "warden":
        outer = _polygon_points(center, ((-8, -radius), (8, -radius), (radius, -8), (radius, 8), (8, radius), (-8, radius), (-radius, 8), (-radius, -8)))
        pygame.draw.polygon(surface, shadow, outer)
        pygame.draw.polygon(surface, color, outer, 4)
        pygame.draw.circle(surface, color, center, radius // 2, 2)
        pygame.draw.line(surface, color, (center[0] - radius // 2, center[1]), (center[0] + radius // 2, center[1]), 3)
        pygame.draw.line(surface, color, (center[0], center[1] - radius // 2), (center[0], center[1] + radius // 2), 3)
    else:
        body = _polygon_points(center, ((0, -radius), (radius, -4), (radius - 5, radius), (0, radius - 5), (-radius + 5, radius), (-radius, -4)))
        pygame.draw.polygon(surface, shadow, body)
        pygame.draw.polygon(surface, color, body, 4)
        pygame.draw.circle(surface, ink, center, 3)


def _oriented_point(
    center: tuple[int, int],
    forward: tuple[int, int],
    right_amount: float,
    forward_amount: float,
) -> tuple[int, int]:
    right = (-forward[1], forward[0])
    return (
        round(center[0] + right[0] * right_amount + forward[0] * forward_amount),
        round(center[1] + right[1] * right_amount + forward[1] * forward_amount),
    )


def draw_player_actor(
    surface: pygame.Surface,
    center: tuple[int, int],
    radius: int,
    pose: str,
    forward: tuple[int, int],
    progress: float,
    color: tuple[int, int, int],
    ink: tuple[int, int, int],
    flash: bool = False,
) -> None:
    """Draw a readable little pilot; pose is presentation-only."""
    if flash:
        color = (255, 255, 255)
    if forward == (0, 0):
        forward = (1, 0)
    cycle = -1 if int(progress * 4) % 2 else 1
    lunge = 5 if pose == "attack" else 7 if pose == "dodge" else -4 if pose == "hurt" else 0
    actor_center = _oriented_point(center, forward, 0, lunge)
    bob = 1 if pose == "idle" and int(progress * 3) % 2 else 0
    actor_center = (actor_center[0], actor_center[1] - bob)
    if pose == "idle":
        breath = 2 + round(progress * 2)
        pygame.draw.circle(surface, color, actor_center, radius + breath, 1)
    shadow_center = _oriented_point(actor_center, forward, 0, -8)
    pygame.draw.ellipse(surface, (8, 18, 25), pygame.Rect(shadow_center[0] - 15, shadow_center[1] - 7, 30, 14))

    head = _oriented_point(actor_center, forward, 0, 9)
    hip = _oriented_point(actor_center, forward, 0, -3)
    shoulder_left = _oriented_point(actor_center, forward, -7, 2)
    shoulder_right = _oriented_point(actor_center, forward, 7, 2)
    leg_swing = 5 * cycle if pose == "move" else 1
    arm_swing = -leg_swing
    left_foot = _oriented_point(actor_center, forward, -6, -13 + leg_swing)
    right_foot = _oriented_point(actor_center, forward, 6, -13 - leg_swing)
    left_hand = _oriented_point(actor_center, forward, -12, arm_swing)
    right_hand = _oriented_point(actor_center, forward, 12, -arm_swing)

    if pose == "attack":
        right_hand = _oriented_point(actor_center, forward, 3, 17)
    elif pose == "skill":
        left_hand = _oriented_point(actor_center, forward, -17, 4)
        right_hand = _oriented_point(actor_center, forward, 17, 4)
        pygame.draw.circle(surface, color, actor_center, radius + round(progress * 8), 2)
        pygame.draw.circle(surface, ink, actor_center, radius // 2 + round(progress * 6), 2)
    elif pose == "dodge":
        left_hand = _oriented_point(actor_center, forward, -10, 10)
        right_hand = _oriented_point(actor_center, forward, 10, 10)
        pygame.draw.line(surface, color, _oriented_point(actor_center, forward, 0, -24), actor_center, 3)
    elif pose == "hurt":
        left_hand = _oriented_point(actor_center, forward, -14, -4)
        right_hand = _oriented_point(actor_center, forward, 14, -4)

    pygame.draw.line(surface, color, hip, left_foot, 5)
    pygame.draw.line(surface, color, hip, right_foot, 5)
    pygame.draw.line(surface, color, shoulder_left, left_hand, 4)
    pygame.draw.line(surface, color, shoulder_right, right_hand, 4)
    torso = _polygon_points(actor_center, ((-7, -5), (-6, 7), (0, 11), (6, 7), (7, -5), (0, -9)))
    pygame.draw.polygon(surface, (20, 48, 62), torso)
    pygame.draw.polygon(surface, color, torso, 3)
    pygame.draw.circle(surface, color, head, 7)
    pygame.draw.circle(surface, ink, head, 3)
    if pose == "attack":
        blade_start = right_hand
        blade_end = _oriented_point(actor_center, forward, 3, 31)
        pygame.draw.line(surface, (255, 255, 255), blade_start, blade_end, 5)
        pygame.draw.line(surface, color, blade_start, blade_end, 2)


def draw_enemy_weapon(
    surface: pygame.Surface,
    center: tuple[int, int],
    target: tuple[int, int],
    kind: str,
    color: tuple[int, int, int],
    phase: float,
    firing: bool,
) -> None:
    dx = target[0] - center[0]
    dy = target[1] - center[1]
    distance = max(1.0, (dx * dx + dy * dy) ** 0.5)
    forward = (dx / distance, dy / distance)
    start = (round(center[0] + forward[0] * 12), round(center[1] + forward[1] * 12))
    if kind == "melee":
        hilt = (round(center[0] + forward[0] * 16), round(center[1] + forward[1] * 16))
        tip = (round(center[0] + forward[0] * 31), round(center[1] + forward[1] * 31))
        pygame.draw.line(surface, (232, 242, 248), hilt, tip, 6)
        pygame.draw.line(surface, color, hilt, tip, 2)
        cross = (-forward[1] * 6, forward[0] * 6)
        pygame.draw.line(surface, color, (round(hilt[0] - cross[0]), round(hilt[1] - cross[1])), (round(hilt[0] + cross[0]), round(hilt[1] + cross[1])), 3)
    elif kind == "ranged":
        muzzle = (round(center[0] + forward[0] * 27), round(center[1] + forward[1] * 27))
        pygame.draw.line(surface, (220, 232, 245), start, muzzle, 8)
        pygame.draw.line(surface, color, start, muzzle, 3)
        pygame.draw.circle(surface, color, muzzle, 5, 2)
        if firing:
            for offset in (0.18, 0.48, 0.78):
                travel = (phase * 0.8 + offset) % 1.0
                bullet = (
                    round(muzzle[0] + (target[0] - muzzle[0]) * travel),
                    round(muzzle[1] + (target[1] - muzzle[1]) * travel),
                )
                pygame.draw.circle(surface, (255, 242, 155), bullet, 5)
                pygame.draw.circle(surface, color, bullet, 7, 2)
