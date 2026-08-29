"""Optional cached synthesized cues; combat logic never depends on audio."""

from __future__ import annotations

from array import array
from math import pi, sin

import pygame


class CueAudio:
    def __init__(self) -> None:
        self.enabled = False
        self.muted = False
        self.master_volume = 0.65
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.music: dict[str, pygame.mixer.Sound] = {}
        self.music_channel: pygame.mixer.Channel | None = None
        self.current_music: str | None = None

    def initialise(self) -> None:
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=22050, size=-16, channels=1)
            pygame.mixer.set_num_channels(max(8, pygame.mixer.get_num_channels()))
            pygame.mixer.set_reserved(1)
            self.music_channel = pygame.mixer.Channel(0)
            self.sounds = {
                "hover": self._tone(460, 32, 0.10),
                "click": self._tone(520, 45, 0.16),
                "slot": self._sequence((480, 620), 70, 0.14),
                "confirm": self._sequence((440, 660), 90, 0.18),
                "move": self._tone(390, 55, 0.12),
                "pull": self._sequence((620, 360), 100, 0.16),
                "impact": self._tone(180, 80, 0.24),
                "impact_heavy": self._sequence((145, 90), 130, 0.28),
                "shield": self._sequence((540, 820), 130, 0.16),
                "shield_hit": self._tone(700, 95, 0.18),
                "damage": self._tone(120, 100, 0.22),
                "enemy_attack": self._sequence((260, 130), 105, 0.22),
                "protocol": self._sequence((620, 780, 940), 180, 0.18),
                "inverse": self._sequence((880, 650, 420), 180, 0.20),
                "anchor": self._sequence((520, 760), 150, 0.18),
                "cancel": self._sequence((420, 780), 110, 0.14),
                "death": self._tone(150, 120, 0.22),
                "reward": self._sequence((620, 760), 160, 0.18),
                "level_clear": self._sequence((520, 660, 820), 240, 0.19),
                "demo_clear": self._sequence((520, 660, 820, 1040), 360, 0.20),
            }
            self.music = {
                "menu": self._music_loop((110, 165, 220, 165, 123, 185, 247, 185), 260, 0.13),
                "battle": self._music_loop((98, 147, 196, 147, 110, 165, 220, 165), 190, 0.12),
                "final": self._music_loop((110, 165, 233, 220, 123, 185, 261, 247), 140, 0.14),
            }
            self.set_volume(self.master_volume)
            self.enabled = True
        except pygame.error:
            self.enabled = False
            self.sounds = {}
            self.music = {}
            self.music_channel = None
            self.current_music = None

    def play(self, cue: str) -> None:
        if self.enabled and not self.muted and cue in self.sounds:
            self.sounds[cue].play()

    def play_music(self, track: str) -> None:
        if not self.enabled or self.music_channel is None or track not in self.music:
            return
        if self.current_music == track and self.music_channel.get_busy():
            return
        self.music_channel.play(self.music[track], loops=-1, fade_ms=280)
        self.current_music = track

    def stop_music(self, fade_ms: int = 240) -> None:
        if self.music_channel is not None:
            self.music_channel.fadeout(max(0, fade_ms))
        self.current_music = None

    def set_muted(self, muted: bool) -> None:
        self.muted = muted
        self._apply_volumes()

    def set_volume(self, volume: float) -> None:
        self.master_volume = max(0.0, min(1.0, volume))
        self._apply_volumes()

    def _apply_volumes(self) -> None:
        audible_volume = 0.0 if self.muted else self.master_volume
        for sound in self.sounds.values():
            sound.set_volume(audible_volume)
        for track in self.music.values():
            track.set_volume(audible_volume * 0.28)

    @staticmethod
    def _tone(frequency: int, duration_ms: int, volume: float) -> pygame.mixer.Sound:
        sample_rate = 22050
        count = sample_rate * duration_ms // 1000
        samples = array(
            "h",
            (
                int(32767 * volume * sin(2 * pi * frequency * index / sample_rate) * (1 - index / count))
                for index in range(count)
            ),
        )
        return pygame.mixer.Sound(buffer=samples)

    @classmethod
    def _sequence(
        cls, frequencies: tuple[int, ...], duration_ms: int, volume: float
    ) -> pygame.mixer.Sound:
        sample_rate = 22050
        count = sample_rate * duration_ms // 1000
        segment = max(1, count // len(frequencies))
        samples = array("h")
        for index in range(count):
            frequency = frequencies[min(len(frequencies) - 1, index // segment)]
            local = index % segment
            envelope = 1 - local / segment
            samples.append(
                int(32767 * volume * sin(2 * pi * frequency * index / sample_rate) * envelope)
            )
        return pygame.mixer.Sound(buffer=samples)

    @staticmethod
    def _music_loop(
        frequencies: tuple[int, ...], step_ms: int, volume: float
    ) -> pygame.mixer.Sound:
        """Build a short looping pulse bed once at startup."""
        sample_rate = 22050
        segment = sample_rate * step_ms // 1000
        count = segment * len(frequencies)
        attack = max(1, sample_rate * 18 // 1000)
        release = max(1, sample_rate * 32 // 1000)
        samples = array("h")
        for index in range(count):
            local = index % segment
            frequency = frequencies[index // segment]
            envelope = min(1.0, local / attack, (segment - local - 1) / release)
            pulse = sin(2 * pi * frequency * index / sample_rate)
            overtone = sin(2 * pi * frequency * 1.5 * index / sample_rate) * 0.32
            samples.append(
                int(32767 * volume * max(0.0, envelope) * (pulse + overtone))
            )
        return pygame.mixer.Sound(buffer=samples)
