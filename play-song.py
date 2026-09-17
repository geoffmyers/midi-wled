"""Play a MIDI file through your instrument, with the LED strip in sync.

File playback with tempo, speed, repeat, fade and terminal-view options.
"""

import argparse
import os
import threading

from mido import MetaMessage, MidiFile, MidiTrack, Message, bpm2tempo, open_output

import led_piano

MIDI_OUTPUT_PORT = "CH345:CH345 MIDI 1 20:0"

MAX_TEMPO = 0xFFFFFF  # set_tempo holds microseconds per beat in 24 bits


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Play MIDI file and control LEDs.")
    parser.add_argument("midi_file", type=str, help="Path to the MIDI file")
    parser.add_argument(
        "--max-velocity", action="store_true", help="Play all notes at maximum velocity (127)"
    )
    parser.add_argument(
        "--piano-only",
        action="store_true",
        help="Play only the parts whose instrument is a piano (General MIDI programs 1-8)",
    )
    parser.add_argument("--bpm", type=int, default=None, help="Play MIDI file at specified BPM")
    parser.add_argument("--repeat", action="store_true", help="Repeat playback on loop")
    parser.add_argument(
        "--speed-percent",
        type=int,
        default=100,
        help="Play MIDI file at a percentage of the original speed (e.g., 50 for half speed)",
    )
    parser.add_argument(
        "--force-piano", action="store_true", help="Switch every part to acoustic grand piano"
    )
    parser.add_argument("--ascii", action="store_true", help="Enable ASCII visualization of MIDI notes")
    parser.add_argument(
        "--fade", action="store_true", help="Enable fading of LEDs when notes are turned off"
    )
    args = parser.parse_args(argv)
    if args.speed_percent <= 0:
        parser.error("--speed-percent must be above 0")
    return args


def parse_midi_info(midi):
    """Extract information about the MIDI file."""
    instruments = set()
    notes = 0
    total_duration = 0
    tempo = 500000  # Default tempo (120 BPM)
    key = "Unknown"

    for track in midi.tracks:
        track_duration = 0
        for msg in track:
            if msg.type == "note_on":
                notes += 1
            if msg.type == "program_change":
                instruments.add(msg.program)
            if msg.type == "set_tempo":
                tempo = msg.tempo
            if msg.type == "key_signature":
                key = msg.key
            track_duration += msg.time
        total_duration = max(total_duration, track_duration)

    tempo_bpm = round(60000000 / tempo)
    song_duration_seconds = total_duration * (tempo / 1e6 / midi.ticks_per_beat)
    return {
        "tracks": len(midi.tracks),
        "instruments": len(instruments),
        "notes": notes,
        "duration": round(song_duration_seconds, 2),
        "tempo_bpm": tempo_bpm,
        "key": key,
        "original_tempo_bpm": tempo_bpm,
    }


def display_midi_info(midi_file, user_bpm=None):
    """Print detailed information about a MIDI file."""
    try:
        midi = MidiFile(midi_file)
        file_size = os.path.getsize(midi_file)
        info = parse_midi_info(midi)

        print("\nMIDI File Information:")
        print(f"  File Name      : {os.path.basename(midi_file)}")
        print(f"  File Size      : {file_size / 1024:.2f} KB")
        print(f"  Total Tracks   : {info['tracks']}")
        print(f"  Total Instruments: {info['instruments']}")
        print(f"  Total Notes    : {info['notes']}")
        print(f"  Duration       : {info['duration']} seconds")
        print(f"  Original Tempo : {info['original_tempo_bpm']} BPM")
        if user_bpm:
            print(f"  User Tempo     : {user_bpm} BPM")
        print(f"  Key Signature  : {info['key']}\n")
    except Exception as e:
        print(f"Error reading MIDI file information: {e}")


def is_piano_program(program):
    """Check if a program change corresponds to a piano instrument (General MIDI 0-7)."""
    return 0 <= program <= 7


def adjust_tempo(midi, tempo_ratio):
    """Return a copy of `midi` with every tempo multiplied by `tempo_ratio`.

    A tempo is microseconds per beat, so a ratio above 1 plays slower. Only the
    tempos change. Scaling the note delays as well applied the change twice (and
    only to notes, not to the pedal and other messages between them), and a
    fresh MidiFile() dropped the file's ticks_per_beat.
    """
    new_midi = MidiFile(type=midi.type, ticks_per_beat=midi.ticks_per_beat)
    has_tempo = any(msg.type == "set_tempo" for track in midi.tracks for msg in track)
    for index, track in enumerate(midi.tracks):
        new_track = MidiTrack()
        if index == 0 and not has_tempo:
            # No tempo event means 120 BPM; state it so there is one to scale.
            new_track.append(MetaMessage("set_tempo", tempo=min(MAX_TEMPO, int(500000 * tempo_ratio)), time=0))
        for msg in track:
            if msg.type == "set_tempo":
                msg = msg.copy(tempo=min(MAX_TEMPO, int(msg.tempo * tempo_ratio)))
            new_track.append(msg)
        new_midi.tracks.append(new_track)
    return new_midi


def rgb_to_ansi(r, g, b):
    """Convert RGB values to ANSI escape codes for terminal color."""
    return f"\033[38;2;{r};{g};{b}m"


class SongPlayer:
    """Plays a MidiFile through an output port while mirroring it on the strip."""

    def __init__(self, strip, base_note=led_piano.BASE_NOTE, fade_leds=False, ascii_visualization=False):
        self.strip = strip
        self.base_note = base_note
        self.fade_leds = fade_leds
        self.ascii_visualization = ascii_visualization
        self.active_notes = set()
        self.note_colors = led_piano.precompute_colors(base_note)

    def print_ascii_visual(self):
        """Print an ASCII visual representation of the active MIDI notes."""
        if not self.ascii_visualization:
            return
        note_visual = [" "] * 88
        for note in self.active_notes:
            if 21 <= note <= 108:
                note_position = note - 21
                base_color = self.note_colors.get(note, [255, 255, 255])
                color_code = rgb_to_ansi(*base_color)
                note_visual[note_position] = f"{color_code}█\033[0m"
        print("".join(note_visual))

    def handle_midi_message(self, msg, max_velocity=False):
        """Process a single MIDI message: light or clear its LEDs."""
        indices = led_piano.led_indices_for_note(msg.note, self.base_note)
        if msg.type == "note_on" and msg.velocity > 0:
            self.active_notes.add(msg.note)
            base_color = self.note_colors.get(msg.note, [0, 0, 0])
            velocity = 127 if max_velocity else msg.velocity
            color = led_piano.adjust_brightness(base_color, velocity)
            self.strip.set_pixels(indices, color)
            self.print_ascii_visual()
        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            self.active_notes.discard(msg.note)
            if self.fade_leds:
                # Each release gets its own thread so a fade doesn't block the
                # next note; LedStrip's internal lock keeps their writes from
                # interleaving on the wire.
                threading.Thread(target=self.strip.fade, args=(indices,), daemon=True).start()
            else:
                self.strip.set_pixels(indices, [0, 0, 0])
            self.print_ascii_visual()

    def play(
        self,
        midi,
        output_port_name,
        *,
        repeat=False,
        force_piano=False,
        piano_only=False,
        max_velocity=False,
    ):
        """Send `midi` to `output_port_name`, lighting the strip as it plays."""
        with open_output(output_port_name) as output:
            while True:
                # The instrument each channel is set to; General MIDI starts on piano.
                channel_program = {}
                if force_piano:
                    for channel in range(16):
                        if channel != 9:
                            output.send(Message("program_change", program=0, channel=channel))
                for msg in midi.play():
                    if msg.type == "program_change":
                        # Program changes go to the instrument too, or every part
                        # plays with whatever sound it already had selected.
                        channel_program[msg.channel] = msg.program
                        output.send(msg.copy(program=0) if force_piano else msg)
                    elif msg.type in ("note_on", "note_off") and msg.channel != 9:
                        is_start = msg.type == "note_on" and msg.velocity > 0
                        if (
                            is_start
                            and piano_only
                            and not is_piano_program(channel_program.get(msg.channel, 0))
                        ):
                            continue  # releases always pass, so no note is left hanging
                        if is_start and max_velocity:
                            msg = msg.copy(velocity=127)
                        self.handle_midi_message(msg, max_velocity=max_velocity)
                        output.send(msg)
                if not repeat:
                    break


def build_midi(midi_file, speed_percent=100, user_bpm=None):
    """Load `midi_file` and apply speed/BPM adjustments, returning the MidiFile
    to play.
    """
    midi = MidiFile(midi_file)

    if speed_percent != 100:
        midi = adjust_tempo(midi, 100.0 / speed_percent)

    if user_bpm:
        original_tempo = None
        for track in midi.tracks:
            for msg in track:
                if msg.type == "set_tempo":
                    original_tempo = msg.tempo
                    break
            if original_tempo:
                break
        if not original_tempo:
            original_tempo = 500000  # Default tempo (120 BPM)
        new_tempo = bpm2tempo(user_bpm)
        tempo_ratio = new_tempo / original_tempo
        midi = adjust_tempo(midi, tempo_ratio)

    return midi


def main():
    args = parse_args()

    strip = led_piano.LedStrip()
    strip.begin()

    display_midi_info(args.midi_file, args.bpm)
    midi = build_midi(args.midi_file, args.speed_percent, args.bpm)
    player = SongPlayer(strip, fade_leds=args.fade, ascii_visualization=args.ascii)

    def _play():
        try:
            player.play(
                midi,
                MIDI_OUTPUT_PORT,
                repeat=args.repeat,
                force_piano=args.force_piano,
                piano_only=args.piano_only,
                max_velocity=args.max_velocity,
            )
        except Exception as e:
            print(f"Error playing MIDI file: {e}")

    playback_thread = threading.Thread(target=_play, daemon=True)
    playback_thread.start()

    options = (
        f"{'maximum velocity ' if args.max_velocity else ''}"
        f"{'piano-only ' if args.piano_only else ''}"
        f"{'repeat ' if args.repeat else ''}"
        f"{f'at {args.speed_percent}% speed ' if args.speed_percent != 100 else ''}"
        f"{'force-piano ' if args.force_piano else ''}"
    )
    print(f"Playing MIDI file '{args.midi_file}' with options: {options}")
    if args.bpm:
        print(f"Tempo set to {args.bpm} BPM.")
    try:
        playback_thread.join()
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        strip.clear()


if __name__ == "__main__":
    main()
