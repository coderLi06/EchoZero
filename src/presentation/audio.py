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

    def initialise(self) -> None:
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=22050, size=-16, channels=1)
            self.sounds = {
                "click": self._tone(520, 45, 0.16),
                "confirm": self._sequence((440, 660), 90, 0.18),
                "move": self._tone(390, 55, 0.12),
                "pull": self._sequence((620, 360), 100, 0.16),
                "impact": self._tone(180, 80, 0.24),
                "impact_heavy": self._sequence((145, 90), 130, 0.28),
                "shield": self._sequence((540, 820), 130, 0.16),
                "shield_hit": self._tone(700, 95, 0.18),
                "damage": self._tone(120, 100, 0.22),
                "protocol": self._sequence((620, 780, 940), 180, 0.18),
                "inverse": self._sequence((880, 650, 420), 180, 0.20),
                "anchor": self._sequence((520, 760), 150, 0.18),
                "cancel": self._sequence((420, 780), 110, 0.14),
                "death": self._tone(150, 120, 0.22),
                "reward": self._sequence((620, 760), 160, 0.18),
                "level_clear": self._sequence((520, 660, 820), 240, 0.19),
                "demo_clear": self._sequence((520, 660, 820, 1040), 360, 0.20),
            }
            self.set_volume(self.master_volume)
            self.enabled = True
        except pygame.error:
            self.enabled = False
            self.sounds = {}

    def play(self, cue: str) -> None:
        if self.enabled and not self.muted and cue in self.sounds:
            self.sounds[cue].play()

    def set_muted(self, muted: bool) -> None:
        self.muted = muted

    def set_volume(self, volume: float) -> None:
        self.master_volume = max(0.0, min(1.0, volume))
        for sound in self.sounds.values():
            sound.set_volume(self.master_volume)

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
