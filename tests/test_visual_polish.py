from types import SimpleNamespace

import pygame

from src.domain import LogicEvent, state_fingerprint
from src.presentation.battle_view import event_detail_label
from src.presentation.effects import (
    EXECUTE_PREP_MS,
    EXECUTE_RESULT_MS,
    playback_state,
    presentation_duration_ms,
    presentation_frame,
)
from src.presentation.stage03_renderer import SAFE_TOP, Stage03Renderer, WINDOW_SIZE
from src.stage03_app import AppScene, Stage03App


def _interactive_first_victory() -> tuple[Stage03App, Stage03Renderer]:
    pygame.font.init()
    app = Stage03App(seed=10303)
    app._start_level()
    renderer = Stage03Renderer(pygame.Surface(WINDOW_SIZE))
    app.renderer = renderer
    for index in (2, 0, 1, 2):
        app._choose_slot(index)
    expected = state_fingerprint(app.preview.state)
    app._execute()
    assert app.ui.verification_ok is True
    assert state_fingerprint(app.level_run.encounter.state) == expected
    assert app.execution_active is True
    assert app.scene is AppScene.BATTLE
    return app, renderer


def test_execute_presentation_delays_reward_without_delaying_combat_fact() -> None:
    app, _ = _interactive_first_victory()
    assert app.level_run.phase.value == "reward"
    assert app._causality_rewrite is True
    rewrite_start = (
        EXECUTE_PREP_MS
        + presentation_duration_ms(app.events, False)
        + EXECUTE_RESULT_MS
        + 1
    )
    app.animation_started_ms = pygame.time.get_ticks() - rewrite_start
    assert app.causality_rewrite_visible is True
    app.animation_started_ms -= 2000
    app._update_presentation_state()
    assert app.execution_active is False
    assert app.scene is AppScene.REWARD


def test_reward_acquisition_commits_after_short_presentation() -> None:
    app, renderer = _interactive_first_victory()
    app.animation_started_ms -= 10000
    app._update_presentation_state()
    choice = app.level_run.reward_choices[0]
    app._choose_reward(0)
    assert app.reward_acquisition == choice
    assert app.level_run.phase.value == "reward"
    renderer.draw(app)
    app._reward_started_ms -= 2000
    app._update_presentation_state()
    assert choice.plugin_id in app.level_run.player_plugins
    assert app.scene is AppScene.BATTLE


def test_event_playback_is_visual_only_and_does_not_mutate_origin() -> None:
    app = Stage03App()
    app._start_level()
    origin = app.level_run.encounter.state.clone()
    before = state_fingerprint(origin)
    preview = app.level_run.encounter.preview()
    frame = presentation_frame(preview.events, 500, False)
    visual = playback_state(origin, preview.events, frame)
    assert state_fingerprint(origin) == before
    assert visual is not origin


def test_internal_ids_are_resolved_to_player_facing_names() -> None:
    pygame.font.init()
    app = Stage03App()
    app._start_level()
    pull = app.level_run.encounter.commands[2]
    assert app.command_label(pull) == "牵引 · 突进体 α"
    renderer = Stage03Renderer(pygame.Surface(WINDOW_SIZE))
    renderer.draw(app)
    visible_text = "\n".join(key[0] for key in renderer.text_cache)
    for banned in ("charger_alpha", "placeholder", "debug", "重启 demo"):
        assert banned not in visible_text.lower()
    event = LogicEvent("plugin_triggered", 1, "player", detail="echo_protocol")
    assert event_detail_label(event, app.battle_view) == "回声协议"


def test_responsive_letterbox_and_pointer_mapping_at_required_sizes() -> None:
    pygame.font.init()
    app = Stage03App()
    assert SAFE_TOP >= 20
    for size, expected in (
        ((1600, 900), pygame.Rect(80, 0, 1440, 900)),
        ((1920, 1080), pygame.Rect(96, 0, 1728, 1080)),
    ):
        output = pygame.Surface(size)
        renderer = Stage03Renderer(output)
        renderer.draw(app)
        assert renderer.viewport == expected
        assert output.get_rect().contains(renderer.viewport)
        assert renderer.to_logical(renderer.viewport.center) == (640, 400)
        assert renderer.to_logical((0, 0)) is None


def test_slot_swap_animation_and_protocol_hover_do_not_change_rules() -> None:
    app = Stage03App()
    app._start_level()
    before = state_fingerprint(app.level_run.encounter.state)
    app._choose_slot(2)
    app._choose_slot(0)
    assert app.ui.swap_pair == (2, 0)
    assert state_fingerprint(app.level_run.encounter.state) == before
    app.ui.protocol_hovered = True
    renderer = Stage03Renderer(pygame.Surface(WINDOW_SIZE))
    renderer.draw(app)
    assert state_fingerprint(app.level_run.encounter.state) == before


def test_rule_flip_frame_remains_compatible_with_read_only_renderer() -> None:
    event = LogicEvent("rule_changed", 5, "reactor", detail="reverse")
    frame = presentation_frame((event,), 100, False)
    assert frame.active_tick == 5
    assert 0.0 < frame.beat_progress < 1.0
    assert SimpleNamespace(frame=frame).frame.event == event
