"""Shared MIDI-to-LED logic for piano-lights.py, play-song.py and learn-song.py.

Before this module existed, each script kept its own copy of the note-to-LED
mapping, colour wheel and brightness scaling (see ARCHITECTURE.md). This is
the one copy: hardware constants, the pure colour/brightness/index math (no
hardware needed, so it is unit-testable without a Raspberry Pi), and a small
thread-safe wrapper around `rpi_ws281x` so concurrent writers (a live note-on
and a `--fade` thread, for example) cannot interleave partial frames on
`strip.show()`.
"""

import time
import threading
from colorsys import hsv_to_rgb

# Hardware defaults for the WS2815 strip and its GPIO wiring.
GPIO_PIN = 18  # GPIO pin connected to the LEDs (PWM pin, use 18 on a Raspberry Pi)
NUM_LEDS = 144  # Total LEDs on the WS2815 strip
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (800kHz for WS2815)
LED_DMA = 10  # DMA channel to use for generating the signal
LED_BRIGHTNESS = 255  # 0 = darkest, 255 = brightest
LED_INVERT = False  # True if using an inverting logic level converter
LED_CHANNEL = 0  # 0 for PWM0

NOTES_IN_OCTAVE = 12
LEDS_PER_NOTE = 2

# MIDI note lit by the first LED pair. 29 = F1 (for reference, the bottom of an
# 88-key piano, A0, is MIDI note 21 -- BASE_NOTE is 8 semitones above it, not
# equal to it).
BASE_NOTE = 29


def led_indices_for_note(note, base_note=BASE_NOTE, leds_per_note=LEDS_PER_NOTE):
    """Return the strip indices a MIDI note lights, in ascending order."""
    start = (note - base_note) * leds_per_note
    return tuple(range(start, start + leds_per_note))


def generate_octave_color(note, base_note=BASE_NOTE):
    """Colour a note by its position within the octave (full HSV colour wheel,
    one full cycle per octave, so every note of the same pitch class matches).
    """
    note_in_octave = (note - base_note) % NOTES_IN_OCTAVE
    hue = note_in_octave / NOTES_IN_OCTAVE
    r, g, b = hsv_to_rgb(hue, 1.0, 1.0)
    return [int(r * 255), int(g * 255), int(b * 255)]


def precompute_colors(base_note=BASE_NOTE, note_range=range(128)):
    """Precompute generate_octave_color() for a range of MIDI notes."""
    return {note: generate_octave_color(note, base_note) for note in note_range}


def adjust_brightness(color, velocity):
    """Scale an [r, g, b] color by MIDI velocity (0-127)."""
    scale = velocity / 127
    return [int(c * scale) for c in color]


class LedStrip:
    """Thread-safe wrapper around rpi_ws281x.PixelStrip.

    Every writer (piano-lights.py's live loop, play-song.py's `--fade`
    threads, learn-song.py's note-on/note-off dispatch) shares one lock, so
    two threads can no longer race to call strip.show() with each other's
    half-written frame.
    """

    def __init__(
        self,
        num_leds=NUM_LEDS,
        gpio_pin=GPIO_PIN,
        freq_hz=LED_FREQ_HZ,
        dma=LED_DMA,
        invert=LED_INVERT,
        brightness=LED_BRIGHTNESS,
        channel=LED_CHANNEL,
    ):
        # Imported lazily so this module (and its pure functions) can be
        # imported and tested on a machine with no rpi_ws281x installed.
        from rpi_ws281x import PixelStrip

        self.num_leds = num_leds
        self._strip = PixelStrip(num_leds, gpio_pin, freq_hz, dma, invert, brightness, channel)
        self._lock = threading.Lock()

    def begin(self):
        self._strip.begin()

    def set_pixels(self, indices, color):
        """Set 0+ LEDs to `color` and push the frame, under the shared lock."""
        from rpi_ws281x import Color

        with self._lock:
            for i in indices:
                if 0 <= i < self.num_leds:
                    self._strip.setPixelColor(i, Color(*color))
            self._strip.show()

    def clear(self):
        self.set_pixels(range(self.num_leds), [0, 0, 0])

    def fade(self, indices, duration=0.5, steps=50):
        """Fade `indices` to black over `duration` seconds, blocking the
        calling thread. The lock is held only per-step (not for the whole
        sleep), so a note-on on another thread is never blocked for more
        than one step's delay -- but every write is still serialised, so a
        fade can never race a set_pixels() call for the same frame.
        """
        from rpi_ws281x import Color

        if steps <= 0:
            self.set_pixels(indices, [0, 0, 0])
            return

        with self._lock:
            valid = [i for i in indices if 0 <= i < self.num_leds]
            start_colors = []
            for i in valid:
                color = self._strip.getPixelColor(i)
                start_colors.append(((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF))

        delay = duration / steps
        for step in range(steps, -1, -1):
            with self._lock:
                for i, (r, g, b) in zip(valid, start_colors):
                    self._strip.setPixelColor(
                        i, Color(int(r * step / steps), int(g * step / steps), int(b * step / steps))
                    )
                self._strip.show()
            if delay:
                time.sleep(delay)
