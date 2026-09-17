"""Real-time MIDI-to-LED piano lighting via aseqdump.

Live mode: parses `aseqdump` output line by line, with sustain-pedal handling.
"""

import subprocess
import threading

import led_piano

MIDI_PORT = "20:0"  # Update with your aseqdump port


class PianoLights:
    """Maps live aseqdump note/control-change lines onto the LED strip."""

    def __init__(self, strip, base_note=led_piano.BASE_NOTE):
        self.strip = strip
        self.base_note = base_note
        self.sustain_active = False
        self.active_notes = set()

    def handle_event(self, event_line):
        """Process a single aseqdump event line."""
        print(f"Received MIDI event: {event_line.strip()}")  # Log the MIDI event

        if "Note on" in event_line:
            parts = event_line.split(",")
            note = int(parts[1].split()[1])
            velocity = int(parts[2].split()[1])
            if velocity > 0:
                indices = led_piano.led_indices_for_note(note, self.base_note)
                color = led_piano.adjust_brightness(
                    led_piano.generate_octave_color(note, self.base_note), velocity
                )
                self.strip.set_pixels(indices, color)
                self.active_notes.add(note)
        elif "Note off" in event_line:
            parts = event_line.split(",")
            note = int(parts[1].split()[1])
            if note in self.active_notes:
                if not self.sustain_active:  # Only turn off LEDs if sustain is not active
                    self.active_notes.remove(note)
                    indices = led_piano.led_indices_for_note(note, self.base_note)
                    self.strip.set_pixels(indices, [0, 0, 0])
        elif "Control change" in event_line:
            parts = event_line.split(",")
            controller = int(parts[1].split()[1])
            value = int(parts[2].split()[1])
            if controller == 64:  # Sustain pedal (Controller 64)
                self.sustain_active = value >= 64
                if not self.sustain_active:
                    # Turn off all LEDs for released notes when sustain is deactivated
                    for note in list(self.active_notes):
                        indices = led_piano.led_indices_for_note(note, self.base_note)
                        self.strip.set_pixels(indices, [0, 0, 0])
                    self.active_notes.clear()

    @staticmethod
    def start_aseqdump(midi_port):
        return subprocess.Popen(["aseqdump", "--port", midi_port], stdout=subprocess.PIPE, text=True)

    def listen(self, midi_port=MIDI_PORT, process_factory=None):
        """Run aseqdump and dispatch its output until it exits or is stopped.

        A dead aseqdump (keyboard unplugged, or the process was never able to
        start) makes `process.stdout.readline()` return "" forever; without
        checking `process.poll()` that is a silent, unthrottled 100%-CPU loop.
        """
        process = (process_factory or self.start_aseqdump)(midi_port)
        try:
            while True:
                line = process.stdout.readline()
                if line == "":
                    if process.poll() is not None:
                        print(
                            f"aseqdump exited (return code {process.poll()}); "
                            "is the MIDI device still connected? Stopping listener."
                        )
                        return
                    # Pipe momentarily empty but process still alive: nothing
                    # to do; readline() already blocks briefly on a live pipe,
                    # so this isn't a busy spin.
                    continue
                if "Note" in line or "Control change" in line:
                    self.handle_event(line)
        finally:
            if process.poll() is None:
                process.terminate()


def main():
    strip = led_piano.LedStrip()
    strip.begin()
    lights = PianoLights(strip)

    midi_thread = threading.Thread(target=lights.listen, daemon=True)
    midi_thread.start()

    print("Listening for MIDI events. Press Ctrl+C to exit.")
    try:
        midi_thread.join()
    except KeyboardInterrupt:
        print("Exiting.")
    finally:
        strip.clear()


if __name__ == "__main__":
    main()
