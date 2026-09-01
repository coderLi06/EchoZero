from pathlib import Path

import pygame

from src.infrastructure.session_metrics import SessionMetrics
from src.presentation.stage03_renderer import (
    TUTORIAL_REPLAY_RECT,
    TUTORIAL_SKIP_ALL_RECT,
    TUTORIAL_SKIP_STEP_RECT,
    Stage03Renderer,
    WINDOW_SIZE,
)
from src.presentation.tutorial import CORE_TUTORIAL_STEPS, ContextualTutorial
from src.stage03_app import AppScene, Stage03App


def test_guided_simulation_shows_core_concepts_once_before_battle() -> None:
    tutorial = ContextualTutorial()
    tutorial.begin_initial()
    seen = []
    while tutorial.current is not None:
        seen.append(tutorial.current.step_id)
        tutorial.advance()
    assert tuple(seen) == CORE_TUTORIAL_STEPS
    assert tutorial.completed is True
    tutorial.begin_initial()
    assert tutorial.current is None


def test_tutorial_supports_skip_step_skip_all_and_explicit_replay() -> None:
    tutorial = ContextualTutorial()
    tutorial.begin_initial()
    first = tutorial.current.step_id
    tutorial.skip_current()
    assert tutorial.current.step_id != first
    tutorial.skip_all()
    assert tutorial.active is False
    assert tutorial.skipped is True
    tutorial.restart()
    assert tutorial.current.step_id == CORE_TUTORIAL_STEPS[0]
    assert tutorial.skipped is False


def test_guided_simulation_blocks_battle_input_and_click_or_tab_advances() -> None:
    app = Stage03App()
    app._start_level()
    turn = app.level_run.encounter.state.turn
    commands = tuple(app.level_run.encounter.commands)
    first = app.tutorial.current.step_id
    app._handle_key(pygame.K_1)
    assert app.tutorial.current.step_id == first
    assert app.ui.selected_slot is None
    app._handle_click((100, 100), 1)
    assert app.tutorial.current.step_id == CORE_TUTORIAL_STEPS[1]
    app._handle_key(pygame.K_TAB)
    assert app.tutorial.current.step_id == CORE_TUTORIAL_STEPS[2]
    assert app.level_run.encounter.state.turn == turn
    assert tuple(app.level_run.encounter.commands) == commands


def test_formal_smoke_has_no_automatic_prompts_after_initial_tutorial() -> None:
    app = Stage03App(seed=10303)
    app._run_flow_smoke()
    assert set(CORE_TUTORIAL_STEPS) <= set(app.tutorial.shown)
    assert app.tutorial.active is False
    assert app.metrics.tutorial_shown == tuple(app.tutorial.shown)


def test_session_metrics_write_privacy_free_summary(tmp_path: Path) -> None:
    metrics = SessionMetrics()
    metrics.start_run(10303)
    metrics.record_turn(
        2,
        "sweep_interference",
        3,
        0,
        ("emergency_barrier", "aegis_counter"),
        "defeat",
    )
    metrics.record_retry()
    metrics.sync_tutorial(["timeline", "level2_order"], False)
    path = tmp_path / "logs" / "session_summary.txt"
    metrics.write(path)
    summary = path.read_text(encoding="utf-8")
    assert "Run Seed: 10303" in summary
    assert "Retry Count: 1" in summary
    assert "First Level 2 Failure:" in summary
    assert "sweep_interference" in summary
    assert "Local only; no personal data" in summary


def test_renderer_exposes_shield_preview_and_reward_relations() -> None:
    pygame.font.init()
    app = Stage03App()
    app._start_level()
    renderer = Stage03Renderer(pygame.Surface(WINDOW_SIZE))
    renderer.draw(app)
    rendered_text = {key[0] for key in renderer.text_cache}
    assert any(text.startswith("CORE 6/6  //  SHIELD") for text in rendered_text)
    assert any(text.startswith("预演终态  CORE") and "SHIELD" in text for text in rendered_text)

    app._run_flow_smoke()
    core = app.plugin_definitions["echo_protocol"]
    assert renderer._build_relation(core, app.level_run).startswith("路线核心")


def test_focus_loss_cancels_only_ui_selection() -> None:
    app = Stage03App()
    app._start_level()
    before = app.level_run.encounter.state.turn
    app._choose_slot(0)
    app._handle_focus_lost()
    assert app.ui.selected_slot is None
    assert app.level_run.encounter.state.turn == before
    assert "不会自动执行" in app.ui.feedback


def test_execute_mouse_debounce_and_tutorial_controls_are_accessible(
    monkeypatch,
) -> None:
    app = Stage03App()
    ticks = iter((1000, 1100, 1200))
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: next(ticks))
    assert app._accept_execute_click() is True
    assert app._accept_execute_click() is False
    assert app._accept_execute_click() is True
    window = pygame.Rect((0, 0), WINDOW_SIZE)
    for rect in (
        TUTORIAL_SKIP_STEP_RECT,
        TUTORIAL_SKIP_ALL_RECT,
        TUTORIAL_REPLAY_RECT,
    ):
        assert window.contains(rect)
        assert rect.height >= 48
    assert pygame.Rect((0, 0), (1600, 900)).contains(window)
    assert pygame.Rect((0, 0), (1920, 1080)).contains(window)
    assert app._handle_key(pygame.K_ESCAPE) is False


def test_clean_battle_replay_button_reopens_tutorial_without_resetting_turn() -> None:
    app = Stage03App()
    app._start_level()
    while app.tutorial.active:
        app._advance_tutorial()
    turn = app.level_run.encounter.state.turn

    app._handle_click(TUTORIAL_REPLAY_RECT.center, 1)

    assert app.tutorial.current.step_id == CORE_TUTORIAL_STEPS[0]
    assert app.level_run.encounter.state.turn == turn


def test_visible_skip_buttons_apply_step_and_all_skip_actions() -> None:
    app = Stage03App()
    app._start_level()
    first = app.tutorial.current.step_id

    app._handle_click(TUTORIAL_SKIP_STEP_RECT.center, 1)
    assert app.tutorial.current.step_id != first
    app._handle_click(TUTORIAL_SKIP_ALL_RECT.center, 1)

    assert app.tutorial.active is False
    assert app.tutorial.skipped is True
    assert app.ui.feedback == ""


def test_renderer_shows_prominent_tutorial_controls_and_highlights_every_step() -> None:
    pygame.font.init()
    app = Stage03App()
    app._start_level()
    renderer = Stage03Renderer(pygame.Surface(WINDOW_SIZE))

    while app.tutorial.active:
        renderer.draw(app)
        assert renderer._tutorial_target_rects(app)
        app._advance_tutorial()

    rendered_text = {key[0] for key in renderer.text_cache}
    assert "TRAINING SIMULATION   1/9" in rendered_text
    assert "跳过本步" in rendered_text
    assert "全部跳过" in rendered_text
    renderer.draw(app)
    clean_text = {key[0] for key in renderer.text_cache}
    assert "重新进入教学" in clean_text
    assert not any("教学完成" in text for text in clean_text)
