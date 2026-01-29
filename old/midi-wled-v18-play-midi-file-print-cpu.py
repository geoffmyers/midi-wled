import threading
import time
import sys
import psutil
from mido import MidiFile, Message, open_output
from colorsys import hsv_to_rgb
from rpi_ws281x import PixelStrip, Color

# Configuration
GPIO_PIN = 18  # GPIO pin connected to the LEDs (PWM pin, use 18 for Raspberry Pi)
NUM_LEDS = 144  # Total LEDs on the WS2815 strip
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (800kHz for WS2815)
LED_DMA = 10  # DMA channel to use for generating the signal
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False  # True if using an inverting logic level converter
LED_CHANNEL = 0  # Set to 0 for PWM0

BASE_NOTE = 29  # MIDI note number for A0 = 21
MIDI_OUTPUT_PORT = "CH345:CH345 MIDI 1 20:0"  # Update with your MIDI output port name

# Ensure MIDI filename is passed as a command-line argument
if len(sys.argv) < 2:
    print("Usage: python script.py <midi_file>")
    sys.exit(1)

MIDI_FILE = sys.argv[1]

# Initialize the LED strip
strip = PixelStrip(NUM_LEDS, GPIO_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

# Sustain pedal state
sustain_pedal_pressed = False

def set_led_color(led_index, color):
    """Set the color of a specific LED on the strip."""
    if 0 <= led_index < NUM_LEDS:
        strip.setPixelColor(led_index, Color(*color))  # Convert to GRB for WS2815
        strip.show()

def generate_octave_color(note):
    """Generate a color based on the note's position within its octave."""
    notes_in_octave = 12
    note_in_octave = (note - BASE_NOTE) % notes_in_octave
    hue = note_in_octave / notes_in_octave
    r, g, b = hsv_to_rgb(hue, 1.0, 1.0)
    return [int(r * 255), int(g * 255), int(b * 255)]

def adjust_brightness(color, velocity):
    """Adjust color brightness based on velocity."""
    brightness_scale = velocity / 127
    return [int(c * brightness_scale) for c in color]

def handle_midi_message(msg):
    """Process a single MIDI message."""
    global sustain_pedal_pressed

    if msg.type == 'control_change' and msg.control == 64:
        # Sustain pedal on/off
        sustain_pedal_pressed = msg.value >= 64
    elif msg.type == 'note_on' and msg.velocity > 0:
        led_index = (msg.note - BASE_NOTE) * 2
        if 0 <= led_index < NUM_LEDS:
            base_color = generate_octave_color(msg.note)
            color = adjust_brightness(base_color, msg.velocity)
            set_led_color(led_index, color)
            set_led_color(led_index + 1, color)
    elif msg.type in ['note_off', 'note_on'] and msg.velocity == 0:
        if not sustain_pedal_pressed:  # Ignore note off if sustain pedal is pressed
            led_index = (msg.note - BASE_NOTE) * 2
            if 0 <= led_index < NUM_LEDS:
                set_led_color(led_index, [0, 0, 0])
                set_led_color(led_index + 1, [0, 0, 0])

def play_midi_file():
    """Play a MIDI file and trigger LEDs."""
    midi = MidiFile(MIDI_FILE)
    with open_output(MIDI_OUTPUT_PORT) as output:
        for msg in midi.play():
            # Ignore messages from Channel 10 (Percussion)
            if msg.type in ['note_on', 'note_off'] and msg.channel == 9:
                continue  # Skip drum/percussion messages

            # Process other channels
            if msg.type in ['note_on', 'note_off', 'control_change']:
                handle_midi_message(msg)
            output.send(msg)

def monitor_cpu_usage():
    """Continuously print CPU usage to stdout."""
    try:
        while True:
            cpu_usage = psutil.cpu_percent(interval=1)
            print(f"CPU Usage: {cpu_usage}%")
    except KeyboardInterrupt:
        pass  # Allow the script to exit cleanly

# Run the MIDI playback and CPU monitoring in separate threads
playback_thread = threading.Thread(target=play_midi_file, daemon=True)
cpu_monitor_thread = threading.Thread(target=monitor_cpu_usage, daemon=True)

playback_thread.start()
cpu_monitor_thread.start()

print(f"Playing MIDI file '{MIDI_FILE}' and controlling LEDs (Drums Ignored). Press Ctrl+C to exit.")
try:
    playback_thread.join()
except KeyboardInterrupt:
    print("Exiting.")
    for i in range(NUM_LEDS):
        set_led_color(i, [0, 0, 0])
