"""Interactive learn-a-song mode: plays a file and blocks on each note until
the keyboard sends it.
"""

import sys
import threading

from mido import MidiFile, open_input, open_output

import led_piano

MIDI_OUTPUT_PORT = "CH345:CH345 MIDI 1 20:0"  # Update with your MIDI output port name
MIDI_INPUT_PORT = "CH345:CH345 MIDI 1 20:0"  # Update with your MIDI input port name


class SongLearner:
    """Lights the next expected note and waits for the player to hit it."""

    def __init__(self, strip, base_note=led_piano.BASE_NOTE):
        self.strip = strip
        self.base_note = base_note

    def handle_midi_message(self, msg):
        """Light (note-on) or clear (note-off) the LEDs for one MIDI message.

        Both branches matter: without the note-off branch actually being
        reached, every LED lit during the song stays lit for the rest of the
        session.
        """
        indices = led_piano.led_indices_for_note(msg.note, self.base_note)
        if msg.type == "note_on" and msg.velocity > 0:
            color = led_piano.adjust_brightness(
                led_piano.generate_octave_color(msg.note, self.base_note), msg.velocity
            )
            self.strip.set_pixels(indices, color)
        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            self.strip.set_pixels(indices, [0, 0, 0])

    @staticmethod
    def wait_for_user_input(input_port, expected_note):
        """Block until the user's keyboard sends `expected_note`.

        Uses the blocking `receive()` rather than polling `iter_pending()` in
        a bare `while True` loop, which pinned a Pi core at 100% between
        notes.
        """
        while True:
            msg = input_port.receive()
            if msg.type == "note_on" and msg.velocity > 0:
                if msg.note == expected_note:
                    print(f"Correct! Played note: {msg.note}")
                    return True
                print(f"Incorrect note. Expected: {expected_note}, but got: {msg.note}")

    def play(self, midi_file, output_port_name, input_port_name):
        """Play `midi_file`, lighting and waiting for each non-drum note."""
        midi = MidiFile(midi_file)
        with open_output(output_port_name) as output, open_input(input_port_name) as input_port:
            for msg in midi.play():
                # Ignore messages from Channel 10 (Percussion)
                if msg.type in ("note_on", "note_off") and msg.channel == 9:
                    output.send(msg)
                    continue

                if msg.type == "note_on" and msg.velocity > 0:
                    self.handle_midi_message(msg)  # Show the note on LEDs
                    output.send(msg)
                    self.wait_for_user_input(input_port, msg.note)
                elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                    self.handle_midi_message(msg)  # Turn the LEDs back off
                    output.send(msg)
                else:
                    output.send(msg)


def main():
    if len(sys.argv) < 2:
        print("Usage: python learn-song.py <midi_file>")
        sys.exit(1)
    midi_file = sys.argv[1]

    strip = led_piano.LedStrip()
    strip.begin()
    learner = SongLearner(strip)

    playback_thread = threading.Thread(
        target=learner.play, args=(midi_file, MIDI_OUTPUT_PORT, MIDI_INPUT_PORT), daemon=True
    )
    playback_thread.start()

    print(f"Playing MIDI file '{midi_file}' and controlling LEDs (Drums Ignored). Press Ctrl+C to exit.")
    try:
        playback_thread.join()
    except KeyboardInterrupt:
        print("Exiting.")
    finally:
        strip.clear()


if __name__ == "__main__":
    main()
