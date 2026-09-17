"""Tests for learn-song.py.

The headline bug (audit finding H): only note_on messages ever reached
handle_midi_message from the playback loop, so its note-off branch was dead
code and every LED lit during a learn session stayed lit for the rest of it.
These tests exercise handle_midi_message directly (dispatch-independent) and
confirm wait_for_user_input no longer busy-waits.
"""


class FakeStrip:
    def __init__(self):
        self.calls = []

    def set_pixels(self, indices, color):
        self.calls.append((tuple(indices), tuple(color)))


class FakeMsg:
    def __init__(self, type, note, velocity, channel=0):
        self.type = type
        self.note = note
        self.velocity = velocity
        self.channel = channel


def test_note_on_lights_leds(load_script_module):
    ls = load_script_module("learn_song", "learn-song.py")
    strip = FakeStrip()
    learner = ls.SongLearner(strip, base_note=29)

    learner.handle_midi_message(FakeMsg("note_on", 29, 100))

    assert len(strip.calls) == 1
    indices, color = strip.calls[0]
    assert indices == (0, 1)
    assert color != (0, 0, 0)


def test_note_off_clears_leds(load_script_module):
    """Regression test for the dead note-off branch."""
    ls = load_script_module("learn_song", "learn-song.py")
    strip = FakeStrip()
    learner = ls.SongLearner(strip, base_note=29)

    learner.handle_midi_message(FakeMsg("note_on", 29, 100))
    learner.handle_midi_message(FakeMsg("note_off", 29, 0))

    assert strip.calls[-1] == ((0, 1), (0, 0, 0))


def test_note_on_velocity_zero_is_treated_as_note_off(load_script_module):
    ls = load_script_module("learn_song", "learn-song.py")
    strip = FakeStrip()
    learner = ls.SongLearner(strip, base_note=29)

    learner.handle_midi_message(FakeMsg("note_on", 29, 100))
    learner.handle_midi_message(FakeMsg("note_on", 29, 0))

    assert strip.calls[-1] == ((0, 1), (0, 0, 0))


def test_play_dispatches_note_off_to_handle_midi_message(load_script_module):
    """Regression test at the dispatch level (not just the handler): the
    playback loop itself must call handle_midi_message for note_off/
    note_on-velocity-0 messages, not only note_on."""
    ls = load_script_module("learn_song", "learn-song.py")
    strip = FakeStrip()
    learner = ls.SongLearner(strip, base_note=29)

    calls = []
    learner.handle_midi_message = lambda msg: calls.append(msg.type)
    # wait_for_user_input is a @staticmethod; overriding it on the instance
    # with a plain function (not bound, since it's found on the instance
    # dict rather than the class) matches its (input_port, note) signature.
    learner.wait_for_user_input = lambda input_port, note: True

    class FakeMidiFile:
        def play(self):
            return iter(
                [
                    FakeMsg("note_on", 29, 100),
                    FakeMsg("note_off", 29, 0),
                ]
            )

    class _NullPort:
        def send(self, msg):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    ls.MidiFile = lambda path: FakeMidiFile()
    ls.open_output = lambda name: _NullPort()
    ls.open_input = lambda name: _NullPort()

    learner.play("dummy.mid", "out", "in")

    assert calls == ["note_on", "note_off"]


class FakeInputPort:
    def __init__(self, messages):
        self._messages = list(messages)
        self.receive_calls = 0

    def receive(self):
        # A real mido input port's receive() blocks until a message arrives;
        # this fake just returns the next canned one. If wait_for_user_input
        # ever goes back to polling iter_pending() in a bare loop, this
        # fixture wouldn't catch the busy-wait directly, but the call count
        # assertion below shows it consumes exactly one message per call
        # rather than spinning.
        self.receive_calls += 1
        return self._messages.pop(0)


def test_wait_for_user_input_blocks_on_receive_until_correct_note(load_script_module, capsys):
    ls = load_script_module("learn_song", "learn-song.py")
    port = FakeInputPort([FakeMsg("note_on", 40, 10), FakeMsg("note_on", 29, 80)])

    result = ls.SongLearner.wait_for_user_input(port, 29)

    assert result is True
    assert port.receive_calls == 2
    out = capsys.readouterr().out
    assert "Incorrect note" in out
    assert "Correct!" in out
