import threading
import time
import sys
import argparse
from mido import MidiFile, MidiTrack, bpm2tempo, open_output, Message, MetaMessage
from colorsys import hsv_to_rgb
from rpi_ws281x import PixelStrip, Color
import os

# Configuration
GPIO_PIN = 18
NUM_LEDS = 144
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 255
LED_INVERT = False
LED_CHANNEL = 0

BASE_NOTE = 29
MIDI_OUTPUT_PORT = "CH345:CH345 MIDI 1 20:0"

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Play MIDI file and control LEDs.")
parser.add_argument("midi_file", type=str, help="Path to the MIDI file")
parser.add_argument("--max-velocity", action="store_true", help="Play all notes at maximum velocity (127)")
parser.add_argument("--piano-only", action="store_true", help="Play only the parts whose instrument is a piano (General MIDI programs 1-8)")
parser.add_argument("--bpm", type=int, default=None, help="Play MIDI file at specified BPM")
parser.add_argument("--repeat", action="store_true", help="Repeat playback on loop")
parser.add_argument("--speed-percent", type=int, default=100, help="Play MIDI file at a percentage of the original speed (e.g., 50 for half speed)")
parser.add_argument("--force-piano", action="store_true", help="Switch every part to acoustic grand piano")
parser.add_argument("--ascii", action="store_true", help="Enable ASCII visualization of MIDI notes")
parser.add_argument("--fade", action="store_true", help="Enable fading of LEDs when notes are turned off")
args = parser.parse_args()

MIDI_FILE = args.midi_file
MAX_VELOCITY = args.max_velocity
PIANO_ONLY = args.piano_only
USER_BPM = args.bpm
REPEAT = args.repeat
SPEED_PERCENT = args.speed_percent
if SPEED_PERCENT <= 0:
    parser.error("--speed-percent must be above 0")
FORCE_PIANO = args.force_piano
ASCII_VISUALIZATION = args.ascii
FADE_LEDS = args.fade

# Initialize LED strip
strip = PixelStrip(NUM_LEDS, GPIO_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

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

def display_midi_info():
    """Display detailed information about the MIDI file."""
    try:
        midi = MidiFile(MIDI_FILE)
        file_size = os.path.getsize(MIDI_FILE)
        info = parse_midi_info(midi)

        print("\nMIDI File Information:")
        print(f"  File Name      : {os.path.basename(MIDI_FILE)}")
        print(f"  File Size      : {file_size / 1024:.2f} KB")
        print(f"  Total Tracks   : {info['tracks']}")
        print(f"  Total Instruments: {info['instruments']}")
        print(f"  Total Notes    : {info['notes']}")
        print(f"  Duration       : {info['duration']} seconds")
        print(f"  Original Tempo : {info['original_tempo_bpm']} BPM")
        if USER_BPM:
            print(f"  User Tempo     : {USER_BPM} BPM")
        print(f"  Key Signature  : {info['key']}\n")
    except Exception as e:
        print(f"Error reading MIDI file information: {e}")

# Precompute colors for all notes
def precompute_colors():
    colors = {}
    for note in range(128):  # MIDI note range
        note_in_octave = (note - BASE_NOTE) % 12
        hue = note_in_octave / 12
        r, g, b = hsv_to_rgb(hue, 1.0, 1.0)
        colors[note] = [int(r * 255), int(g * 255), int(b * 255)]
    return colors

NOTE_COLORS = precompute_colors()

def adjust_brightness(color, velocity):
    """Adjust color brightness based on velocity."""
    scale = velocity / 127
    return [int(c * scale) for c in color]

def set_leds(indices, color):
    """Set multiple LEDs and update the strip."""
    for i in indices:
        if 0 <= i < NUM_LEDS:
            strip.setPixelColor(i, Color(*color))
    strip.show()

# Store active notes for simultaneous display
active_notes = set()

def rgb_to_ansi(r, g, b):
    """Convert RGB values to ANSI escape codes for terminal color."""
    return f"\033[38;2;{r};{g};{b}m"

def print_ascii_visual():
    """Print an ASCII visual representation of the active MIDI notes."""
    if not ASCII_VISUALIZATION:
        return
    note_visual = [" "] * 88
    for note in active_notes:
        if 21 <= note <= 108:
            note_position = note - 21
            base_color = NOTE_COLORS.get(note, [255, 255, 255])
            color_code = rgb_to_ansi(*base_color)
            note_visual[note_position] = f"{color_code}█\033[0m"
    print("".join(note_visual))

def fade_off_leds(indices, duration=0.5):
    """Fade off multiple LEDs over the specified duration."""
    steps = 50
    delay = duration / steps

    def fade():
        for step in range(steps, -1, -1):
            for i in indices:
                if 0 <= i < NUM_LEDS:
                    color = strip.getPixelColor(i)
                    r = (color >> 16) & 0xFF
                    g = (color >> 8) & 0xFF
                    b = color & 0xFF
                    r = int(r * step / steps)
                    g = int(g * step / steps)
                    b = int(b * step / steps)
                    strip.setPixelColor(i, Color(r, g, b))
            strip.show()
            time.sleep(delay)

    threading.Thread(target=fade, daemon=True).start()

def handle_midi_message(msg):
    """Process a single MIDI message."""
    if msg.type == 'note_on' and msg.velocity > 0:
        active_notes.add(msg.note)
        led_indices = [(msg.note - BASE_NOTE) * 2, (msg.note - BASE_NOTE) * 2 + 1]
        base_color = NOTE_COLORS.get(msg.note, [0, 0, 0])
        velocity = 127 if MAX_VELOCITY else msg.velocity
        color = adjust_brightness(base_color, velocity)
        set_leds(led_indices, color)
        print_ascii_visual()  # Print ASCII visual
    elif msg.type in ['note_off', 'note_on'] and msg.velocity == 0:
        active_notes.discard(msg.note)
        led_indices = [(msg.note - BASE_NOTE) * 2, (msg.note - BASE_NOTE) * 2 + 1]
        if FADE_LEDS:
            fade_off_leds(led_indices)  # Fade off LEDs
        else:
            set_leds(led_indices, [0, 0, 0])  # Turn off LEDs immediately
        print_ascii_visual()  # Print ASCII visual

def is_piano_program(program):
    """Check if a program change corresponds to a piano instrument (General MIDI 0–7)."""
    return 0 <= program <= 7

MAX_TEMPO = 0xFFFFFF  # set_tempo holds microseconds per beat in 24 bits

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

def play_midi_file():
    """Play a MIDI file and trigger LEDs."""
    try:
        midi = MidiFile(MIDI_FILE)

        # Adjust playback speed: 50% speed means each beat lasts twice as long
        if SPEED_PERCENT != 100:
            midi = adjust_tempo(midi, 100.0 / SPEED_PERCENT)

        # Adjust playback tempo
        if USER_BPM:
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
            new_tempo = bpm2tempo(USER_BPM)
            tempo_ratio = new_tempo / original_tempo
            midi = adjust_tempo(midi, tempo_ratio)

        with open_output(MIDI_OUTPUT_PORT) as output:
            while True:
                # The instrument each channel is set to; General MIDI starts on piano.
                channel_program = {}
                if FORCE_PIANO:
                    for channel in range(16):
                        if channel != 9:
                            output.send(Message('program_change', program=0, channel=channel))
                for msg in midi.play():
                    if msg.type == 'program_change':
                        # Program changes go to the instrument too, or every part
                        # plays with whatever sound it already had selected.
                        channel_program[msg.channel] = msg.program
                        output.send(msg.copy(program=0) if FORCE_PIANO else msg)
                    elif msg.type in ['note_on', 'note_off'] and msg.channel != 9:
                        is_start = msg.type == 'note_on' and msg.velocity > 0
                        if (is_start and PIANO_ONLY
                                and not is_piano_program(channel_program.get(msg.channel, 0))):
                            continue  # releases always pass, so no note is left hanging
                        if is_start and MAX_VELOCITY:
                            msg = msg.copy(velocity=127)
                        handle_midi_message(msg)
                        output.send(msg)
                if not REPEAT:
                    break
    except Exception as e:
        print(f"Error playing MIDI file: {e}")

# Display MIDI file information
display_midi_info()

# Run MIDI playback in a separate thread
playback_thread = threading.Thread(target=play_midi_file, daemon=True)
playback_thread.start()

print(f"Playing MIDI file '{MIDI_FILE}' with options: {'maximum velocity ' if MAX_VELOCITY else ''}{'piano-only ' if PIANO_ONLY else ''}{'repeat ' if REPEAT else ''}{f'at {SPEED_PERCENT}% speed ' if SPEED_PERCENT != 100 else ''}{'force-piano ' if FORCE_PIANO else ''}")
if USER_BPM:
    print(f"Tempo set to {USER_BPM} BPM.")
try:
    playback_thread.join()
except KeyboardInterrupt:
    print("\nExiting...")
    for i in range(NUM_LEDS):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
