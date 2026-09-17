"""Tests for the shared note-to-LED mapping, colour, brightness math and the
thread-safe LedStrip wrapper -- the module every script now imports instead
of keeping its own copy (ARCHITECTURE.md)."""

import threading
import time

import led_piano


def test_led_indices_for_note_at_base_note():
    assert led_piano.led_indices_for_note(led_piano.BASE_NOTE) == (0, 1)


def test_led_indices_for_note_offset():
    assert led_piano.led_indices_for_note(led_piano.BASE_NOTE + 5) == (10, 11)


def test_led_indices_for_note_below_base_note_goes_negative():
    # Callers are expected to range-check before writing; the mapping itself
    # is just arithmetic.
    assert led_piano.led_indices_for_note(led_piano.BASE_NOTE - 1) == (-2, -1)


def test_generate_octave_color_same_pitch_class_matches_across_octaves():
    middle_c = led_piano.generate_octave_color(60)
    octave_up = led_piano.generate_octave_color(72)
    octave_down = led_piano.generate_octave_color(48)
    assert middle_c == octave_up == octave_down


def test_generate_octave_color_base_note_is_pure_red():
    assert led_piano.generate_octave_color(led_piano.BASE_NOTE, base_note=led_piano.BASE_NOTE) == [
        255,
        0,
        0,
    ]


def test_generate_octave_color_wraps_every_twelve_semitones():
    colors = {
        tuple(led_piano.generate_octave_color(note))
        for note in range(led_piano.BASE_NOTE, led_piano.BASE_NOTE + 12)
    }
    # 12 distinct hues, one per semitone.
    assert len(colors) == 12


def test_precompute_colors_matches_generate_octave_color_for_every_note():
    colors = led_piano.precompute_colors()
    assert len(colors) == 128
    for note in (0, 21, 29, 60, 100, 127):
        assert colors[note] == led_piano.generate_octave_color(note)


def test_adjust_brightness_full_velocity_is_unchanged():
    assert led_piano.adjust_brightness([100, 200, 50], 127) == [100, 200, 50]


def test_adjust_brightness_zero_velocity_is_black():
    assert led_piano.adjust_brightness([100, 200, 50], 0) == [0, 0, 0]


def test_adjust_brightness_scales_proportionally():
    result = led_piano.adjust_brightness([200, 200, 200], 64)
    # 64/127 ~= 0.504
    assert result == [100, 100, 100]


def test_led_strip_set_pixels_writes_and_shows_once():
    strip = led_piano.LedStrip(num_leds=8)
    strip.begin()
    strip.set_pixels([0, 1], [10, 20, 30])

    assert strip._strip.began is True
    assert strip._strip.getPixelColor(0) == (10 << 16) | (20 << 8) | 30
    assert strip._strip.getPixelColor(1) == (10 << 16) | (20 << 8) | 30
    assert strip._strip.show_calls == 1


def test_led_strip_set_pixels_ignores_out_of_range_indices():
    strip = led_piano.LedStrip(num_leds=4)
    strip.begin()
    strip.set_pixels([-1, 0, 4, 99], [1, 2, 3])
    assert strip._strip.getPixelColor(0) == (1 << 16) | (2 << 8) | 3


def test_led_strip_clear_zeroes_every_pixel():
    strip = led_piano.LedStrip(num_leds=4)
    strip.begin()
    strip.set_pixels([0, 1, 2, 3], [9, 9, 9])
    strip.clear()
    for i in range(4):
        assert strip._strip.getPixelColor(i) == 0


def test_led_strip_fade_ends_at_black():
    strip = led_piano.LedStrip(num_leds=2)
    strip.begin()
    strip.set_pixels([0], [100, 100, 100])
    strip.fade([0], duration=0.01, steps=5)
    assert strip._strip.getPixelColor(0) == 0


def test_led_strip_fade_zero_steps_turns_off_immediately():
    strip = led_piano.LedStrip(num_leds=2)
    strip.begin()
    strip.set_pixels([0], [100, 100, 100])
    strip.fade([0], duration=0.01, steps=0)
    assert strip._strip.getPixelColor(0) == 0


def test_led_strip_serialises_concurrent_writers():
    """Regression test for the `--fade` race: two threads used to be able to
    call strip.show() concurrently. Wrap the fake strip's setPixelColor/show
    with a second, independent lock that fails non-blocking acquisition if
    anything is already inside -- if LedStrip's own lock stopped serialising
    writes, this would catch it.
    """
    strip = led_piano.LedStrip(num_leds=4)
    strip.begin()

    guard = threading.Lock()
    violations = []
    orig_set = strip._strip.setPixelColor
    orig_show = strip._strip.show

    def guarded_set(index, color):
        if not guard.acquire(blocking=False):
            violations.append("setPixelColor")
            return
        try:
            orig_set(index, color)
        finally:
            guard.release()

    def guarded_show():
        if not guard.acquire(blocking=False):
            violations.append("show")
            return
        try:
            orig_show()
            time.sleep(0.001)  # widen the window a race would need
        finally:
            guard.release()

    strip._strip.setPixelColor = guarded_set
    strip._strip.show = guarded_show

    def writer(color):
        for _ in range(10):
            strip.set_pixels([0, 1], color)

    threads = [threading.Thread(target=writer, args=([i, i, i],)) for i in (1, 2, 3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert violations == []
