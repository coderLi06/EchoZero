import pygame
from types import SimpleNamespace

from src.domain import LogicEvent, TimelineRule, state_fingerprint
from src.presentation.audio import CueAudio
from src.presentation.effects import (
    BASE_EVENT_MS,
    EVENT_CUES,
    REDUCED_EVENT_MS,
    PresentationFrame,
    cue_for_event,
    plugin_feedback,
    presentation_frame,
)
from src.presentation.stage03_renderer import (
    EXECUTE_RECT,
    RESULT_RESTART_RECT,
    REWARD_RECTS,
    SLOT_RECTS,
    Stage03Renderer,
    WINDOW_SIZE,
)
from src.stage03_app import AppScene, Stage03App


def test_presentation_timeline_reads_events_without_mutating_game_fact() -> None:
    app = Stage03App()
    app._start_level()
    before = state_fingerprint(app.level_run.encounter.state)
    event = LogicEvent("moved", 1, "player")
    frame = presentation_frame((event,), BASE_EVENT_MS // 2, False)
    assert frame.event == event
    assert 0.45 < frame.progress < 0.55
    assert state_fingerprint(app.level_run.encounter.state) == before


def test_reduced_motion_shortens_animation_and_disables_shake() -> None:
    event = LogicEvent("push_blocked", 1, "player")
    normal = presentation_frame((event,), 30, False)
    reduced = presentation_frame((event,), 30, True)
    assert normal.shake != (0, 0)
    assert reduced.shake == (0, 0)
    assert reduced.progress == 30 / REDUCED_EVENT_MS


def test_protocol_feedback_and_key_event_cues_are_explicit() -> None:
    protocol = LogicEvent("plugin_triggered", 3, "player", detail="echo_protocol")
    assert plugin_feedback(protocol) == "回声协议 · 重放首拍"
    assert cue_for_event(protocol) == "protocol"
    assert {
        "moved", "pushed", "shielded", "damaged", "died",
        "plugin_triggered", "rule_changed", "rule_held",
    } <= EVENT_CUES.keys()


def test_audio_controls_are_safe_before_initialisation() -> None:
    audio = CueAudio()
    audio.set_volume(2.0)
    audio.set_muted(True)
    audio.play("missing")
    assert audio.master_volume == 1.0
    assert audio.muted is True
    assert audio.enabled is False


def test_missing_audio_device_degrades_without_crashing(monkeypatch) -> None:
    audio = CueAudio()

    def unavailable():
        raise pygame.error("no audio device")

    monkeypatch.setattr(pygame.mixer, "get_init", unavailable)
    audio.initialise()
    assert audio.enabled is False
    assert audio.sounds == {}


def test_accessibility_settings_persist_across_restart_and_level_transition() -> None:
    app = Stage03App()
    app._handle_key(pygame.K_m)
    app._handle_key(pygame.K_F2)
    app._handle_key(pygame.K_MINUS)
    app._start_level()
    assert app.ui.muted is True
    assert app.ui.reduced_motion is True
    assert app.ui.volume_percent == 55

    app.level_index = 0
    app.scene = AppScene.TRANSITION
    app._start_next_level()
    assert app.ui.muted is True
    assert app.ui.reduced_motion is True
    assert app.ui.volume_percent == 55


def test_renderer_draw_does_not_change_domain_state() -> None:
    pygame.font.init()
    app = Stage03App()
    app._start_level()
    screen = pygame.Surface(WINDOW_SIZE)
    renderer = Stage03Renderer(screen)
    before = state_fingerprint(app.level_run.encounter.state)
    renderer.draw(app)
    assert state_fingerprint(app.level_run.encounter.state) == before
    assert renderer.text_cache


def test_primary_ui_targets_fit_and_do_not_overlap() -> None:
    window = pygame.Rect((0, 0), WINDOW_SIZE)
    controls = (*SLOT_RECTS, EXECUTE_RECT, RESULT_RESTART_RECT, *REWARD_RECTS)
    assert all(window.contains(rect) for rect in controls)
    assert all(rect.height >= 48 for rect in controls)
    assert all(not left.colliderect(right) for left, right in zip(REWARD_RECTS, REWARD_RECTS[1:]))
    assert all(not slot.colliderect(EXECUTE_RECT) for slot in SLOT_RECTS)


def test_global_accessibility_status_fits_its_reserved_footer() -> None:
    pygame.font.init()
    renderer = Stage03Renderer(pygame.Surface(WINDOW_SIZE))
    status = "M 音频  100%   ·   -/+ 音量   ·   F2 减弱动态   ·   F3 调试关"
    assert renderer._surface(status, 12, (166, 183, 207)).get_width() <= 480


def test_hud_rule_follows_the_event_being_presented_before_final_state() -> None:
    events = (
        LogicEvent("rule_triggered", 0, "reactor", detail="reverse"),
        LogicEvent("moved", 1, "player"),
        LogicEvent("rule_changed", 5, "reactor", detail="stable"),
    )
    app = SimpleNamespace(
        events=events,
        presentation=PresentationFrame(events[1], 1, 0.5, (0, 0)),
    )
    assert Stage03Renderer._display_rule(app, TimelineRule.STABLE) is TimelineRule.REVERSE
    app.presentation = PresentationFrame(events[2], 2, 0.2, (0, 0))
    assert Stage03Renderer._display_rule(app, TimelineRule.STABLE) is TimelineRule.STABLE
