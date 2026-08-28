"""Tiny optional synthesized cue layer; combat logic never depends on audio."""

from __future__ import annotations

from array import array
from math import pi, sin

import pygame


class CueAudio:
    def __init__(self) -> None:
        self.enabled = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}

    def initialise(self) -> None:
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=22050, size=-16, channels=1)
            self.sounds = {
                "click": self._tone(520, 45, 0.16),
                "execute": self._tone(300, 90, 0.20),
                "plugin": self._tone(760, 150, 0.22),
                "death": self._tone(150, 120, 0.22),
                "victory": self._tone(920, 260, 0.20),
            }
            self.enabled = True
        except pygame.error:
            self.enabled = False

    def play(self, cue: str) -> None:
        if self.enabled and cue in self.sounds:
            self.sounds[cue].play()

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
