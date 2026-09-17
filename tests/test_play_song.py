"""Tests for play-song.py: adjust_tempo() (using an in-memory mido.MidiFile,
no file on disk) and the note-off dispatch through handle_midi_message,
including the `--fade` path that used to race on strip.show()."""

import time

from mido import MetaMessage, MidiFile, MidiTrack, Message


def _midi_with_tempo(tempo, ticks_per_beat=480):
    midi = MidiFile(ticks_per_beat=ticks_per_beat)
    track = MidiTrack()
    track.append(MetaMessage("set_tempo", tempo=tempo, time=0))
    track.append(Message("note_on", note=60, velocity=64, time=0))
    track.append(Message("note_off", note=60, velocity=0, time=480))
    midi.tracks.append(track)
    return midi


def test_adjust_tempo_scales_existing_tempo(load_script_module):
    ps = load_script_module("play_song", "play-song.py")
    midi = _midi_with_tempo(500000)  # 120 BPM

    scaled = ps.adjust_tempo(midi, 2.0)  # half speed -> double the tempo value

    tempos = [msg.tempo for msg in scaled.tracks[0] if msg.type == "set_tempo"]
    assert tempos == [1000000]


def test_adjust_tempo_preserves_ticks_per_beat(load_script_module):
    ps = load_script_module("play_song", "play-song.py")
    midi = _midi_with_tempo(500000, ticks_per_beat=960)

    scaled = ps.adjust_tempo(midi, 1.5)

    assert scaled.ticks_per_beat == 960


def test_adjust_tempo_does_not_touch_note_timing(load_script_module):
    """Scaling note delays as well as tempo applied the change twice; this is
    the regression the function's own docstring warns about."""
    ps = load_script_module("play_song", "play-song.py")
    midi = _midi_with_tempo(500000)

    scaled = ps.adjust_tempo(midi, 2.0)

    original_times = [msg.time for msg in midi.tracks[0] if msg.type in ("note_on", "note_off")]
    scaled_times = [msg.time for msg in scaled.tracks[0] if msg.type in ("note_on", "note_off")]
    assert scaled_times == original_times


def test_adjust_tempo_injects_implicit_120bpm_when_no_tempo_event(load_script_module):
    ps = load_script_module("play_song", "play-song.py")
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    track.append(Message("note_on", note=60, velocity=64, time=0))
    midi.tracks.append(track)

    scaled = ps.adjust_tempo(midi, 2.0)

    tempos = [msg.tempo for msg in scaled.tracks[0] if msg.type == "set_tempo"]
    assert tempos == [1000000]  # 500000 (implicit 120 BPM) * 2


def test_adjust_tempo_caps_at_24_bit_max(load_script_module):
    ps = load_script_module("play_song", "play-song.py")
    midi = _midi_with_tempo(500000)

    scaled = ps.adjust_tempo(midi, 1000.0)

    tempos = [msg.tempo for msg in scaled.tracks[0] if msg.type == "set_tempo"]
    assert tempos == [ps.MAX_TEMPO]


class FakeStrip:
    def __init__(self):
        self.calls = []
        self.fade_calls = []

    def set_pixels(self, indices, color):
        self.calls.append((tuple(indices), tuple(color)))

    def fade(self, indices, duration=0.5, steps=50):
        self.fade_calls.append(tuple(indices))
        self.calls.append((tuple(indices), (0, 0, 0)))


class FakeMsg:
    def __init__(self, type, note, velocity, channel=0):
        self.type = type
        self.note = note
        self.velocity = velocity
        self.channel = channel

    def copy(self, **kwargs):
        attrs = {"type": self.type, "note": self.note, "velocity": self.velocity, "channel": self.channel}
        attrs.update(kwargs)
        return FakeMsg(**attrs)


def test_note_off_dispatch_clears_leds_without_fade(load_script_module):
    ps = load_script_module("play_song", "play-song.py")
    strip = FakeStrip()
    player = ps.SongPlayer(strip, base_note=29, fade_leds=False)

    player.handle_midi_message(FakeMsg("note_on", 29, 100))
    player.handle_midi_message(FakeMsg("note_off", 29, 0))

    assert strip.calls[-1] == ((0, 1), (0, 0, 0))
    assert 29 not in player.active_notes


def test_note_off_dispatch_with_fade_uses_strip_fade_not_set_pixels(load_script_module):
    """Regression test for the `--fade` race: before the fix, every release
    spawned a thread that called strip.show() with no coordination with any
    other writer. The fade path must now go through LedStrip.fade(), which
    serialises with every other writer under one lock."""
    ps = load_script_module("play_song", "play-song.py")
    strip = FakeStrip()
    player = ps.SongPlayer(strip, base_note=29, fade_leds=True)

    player.handle_midi_message(FakeMsg("note_on", 29, 100))
    player.handle_midi_message(FakeMsg("note_off", 29, 0))
    for _ in range(50):
        if strip.fade_calls:
            break
        time.sleep(0.01)

    assert strip.fade_calls == [(0, 1)]


def test_note_on_velocity_zero_is_treated_as_note_off(load_script_module):
    ps = load_script_module("play_song", "play-song.py")
    strip = FakeStrip()
    player = ps.SongPlayer(strip, base_note=29, fade_leds=False)

    player.handle_midi_message(FakeMsg("note_on", 29, 100))
    player.handle_midi_message(FakeMsg("note_on", 29, 0))

    assert strip.calls[-1] == ((0, 1), (0, 0, 0))


def test_max_velocity_overrides_note_color_brightness(load_script_module):
    ps = load_script_module("play_song", "play-song.py")
    strip = FakeStrip()
    player = ps.SongPlayer(strip, base_note=29, fade_leds=False)

    player.handle_midi_message(FakeMsg("note_on", 29, 10), max_velocity=True)

    _, color = strip.calls[0]
    assert color == tuple(player.note_colors[29])  # full brightness, unscaled
