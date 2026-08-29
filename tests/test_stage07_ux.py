from pathlib import Path

import pygame

from src.infrastructure.session_metrics import SessionMetrics
from src.presentation.stage03_renderer import (
    TUTORIAL_NEXT_RECT,
    TUTORIAL_SKIP_RECT,
    Stage03Renderer,
    WINDOW_SIZE,
)
from src.presentation.tutorial import ContextualTutorial, LEVEL_ONE_STEPS
from src.stage03_app import AppScene, Stage03App


def test_contextual_tutorial_shows_each_level_one_concept_once() -> None:
    tutorial = ContextualTutorial()
    tutorial.begin_level_one()
    seen = []
    while tutorial.current is not None:
        seen.append(tutorial.current.step_id)
        tutorial.advance()
    assert tuple(seen) == LEVEL_ONE_STEPS
    tutorial.begin_level_one()
    assert tutorial.current is None


def test_tutorial_can_be_skipped_and_stays_skipped_across_restart() -> None:
    app = Stage03App()
    app._start_level()
    assert app.tutorial.current is not None
    app._handle_key(pygame.K_F1)
    assert app.tutorial.skipped is True
    assert app.tutorial.current is None
    app._start_level()
    assert app.tutorial.current is None
    assert app.metrics.tutorial_skipped is True


def test_standard_first_turn_progresses_contextual_tutorial() -> None:
    app = Stage03App()
    app._start_level()
    assert app.tutorial.current.step_id == "timeline"
    app._choose_slot(2)
    assert app.tutorial.current.step_id == "input"
    app._choose_slot(0)
    assert app.tutorial.current.step_id == "intent"
    app._choose_slot(1)
    assert app.tutorial.current.step_id == "preview"
    app._choose_slot(2)
    assert app.tutorial.current.step_id == "execute"
    app._execute()
    assert app.scene is AppScene.REWARD
    assert app.tutorial.current is None


def test_formal_smoke_covers_level_two_tutorial_and_phase_switch() -> None:
    app = Stage03App(seed=10303)
    app._run_flow_smoke()
    assert {
        "level2_order",
        "anchor",
        "phase_switch",
    } <= set(app.tutorial.shown)
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
    assert any(text.startswith("CORE  6/6   /   SHIELD") for text in rendered_text)
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


def test_execute_mouse_debounce_and_tutorial_targets_are_accessible(
    monkeypatch,
) -> None:
    app = Stage03App()
    ticks = iter((1000, 1100, 1200))
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: next(ticks))
    assert app._accept_execute_click() is True
    assert app._accept_execute_click() is False
    assert app._accept_execute_click() is True
    window = pygame.Rect((0, 0), WINDOW_SIZE)
    assert window.contains(TUTORIAL_NEXT_RECT)
    assert window.contains(TUTORIAL_SKIP_RECT)
    assert TUTORIAL_NEXT_RECT.height >= 48
    assert TUTORIAL_SKIP_RECT.height >= 48
    assert pygame.Rect((0, 0), (1600, 900)).contains(window)
    assert pygame.Rect((0, 0), (1920, 1080)).contains(window)
    assert app._handle_key(pygame.K_ESCAPE) is False
