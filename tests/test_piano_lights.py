"""Tests for piano-lights.py: aseqdump line parsing, sustain handling, and
the fix for the silent 100%-CPU loop when aseqdump exits."""


class FakeStrip:
    def __init__(self):
        self.calls = []

    def set_pixels(self, indices, color):
        self.calls.append((tuple(indices), tuple(color)))


def _note_on(note, velocity):
    return f"Note on                  0, note {note}, velocity {velocity}"


def _note_off(note):
    return f"Note off                 0, note {note}, velocity 0"


def _control_change(controller, value):
    return f"Control change            0, controller {controller}, value {value}"


def test_note_on_lights_two_leds(load_script_module):
    pl = load_script_module("piano_lights", "piano-lights.py")
    strip = FakeStrip()
    lights = pl.PianoLights(strip, base_note=29)

    lights.handle_event(_note_on(29, 100))

    assert len(strip.calls) == 1
    indices, color = strip.calls[0]
    assert indices == (0, 1)
    assert color != (0, 0, 0)
    assert 29 in lights.active_notes


def test_note_off_clears_leds(load_script_module):
    pl = load_script_module("piano_lights", "piano-lights.py")
    strip = FakeStrip()
    lights = pl.PianoLights(strip, base_note=29)

    lights.handle_event(_note_on(29, 100))
    lights.handle_event(_note_off(29))

    assert strip.calls[-1] == ((0, 1), (0, 0, 0))
    assert 29 not in lights.active_notes


def test_note_off_suppressed_while_sustain_held(load_script_module):
    pl = load_script_module("piano_lights", "piano-lights.py")
    strip = FakeStrip()
    lights = pl.PianoLights(strip, base_note=29)

    lights.handle_event(_control_change(64, 127))  # sustain pedal down
    lights.handle_event(_note_on(29, 100))
    lights.handle_event(_note_off(29))

    # The note-off was suppressed: the last write is still the "on" color.
    assert strip.calls[-1] != ((0, 1), (0, 0, 0))
    assert 29 in lights.active_notes


def test_sustain_release_clears_every_held_note(load_script_module):
    pl = load_script_module("piano_lights", "piano-lights.py")
    strip = FakeStrip()
    lights = pl.PianoLights(strip, base_note=29)

    lights.handle_event(_control_change(64, 127))  # sustain down
    lights.handle_event(_note_on(29, 100))
    lights.handle_event(_control_change(64, 0))  # sustain up

    assert strip.calls[-1] == ((0, 1), (0, 0, 0))
    assert lights.active_notes == set()


class FakeAseqdumpProcess:
    """A canned aseqdump-like process object: yields a fixed list of lines,
    then behaves like an exited process (EOF on stdout, poll() non-None)."""

    def __init__(self, lines, exit_code=1):
        self._lines = list(lines)
        self._exit_code = exit_code
        self.stdout = self
        self.terminated = False

    def readline(self):
        if self._lines:
            return self._lines.pop(0)
        return ""

    def poll(self):
        return None if self._lines else self._exit_code

    def terminate(self):
        self.terminated = True


def test_listen_processes_events_then_stops_cleanly_on_exit(load_script_module, capsys):
    """Regression test: readline() on a dead aseqdump returns "" forever.
    Before the fix, this loop never checked process.poll() and spun at
    100% CPU without ever logging why. It must now notice the exit, log it,
    and return instead of looping."""
    pl = load_script_module("piano_lights", "piano-lights.py")
    strip = FakeStrip()
    lights = pl.PianoLights(strip, base_note=29)
    process = FakeAseqdumpProcess([_note_on(29, 100), _note_off(29)], exit_code=1)

    lights.listen(process_factory=lambda port: process)

    assert len(strip.calls) == 2  # both events were handled before exit
    out = capsys.readouterr().out
    assert "aseqdump exited" in out
