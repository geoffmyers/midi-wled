import threading
import random
import subprocess
import time
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
MIDI_PORT = "20:0"  # Update with your aseqdump port

# State variables
sustain_active = False
active_notes = set()
fading_leds = {}  # Dictionary to track fading LEDs {led_index: [r, g, b, steps_remaining]}

# Initialize the LED strip
strip = PixelStrip(NUM_LEDS, GPIO_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

def set_led_color(led_index, color):
    """Set the color of a specific LED on the strip."""
    if 0 <= led_index < NUM_LEDS:
        strip.setPixelColor(led_index, Color(*color))  # Convert to GRB for WS2815

def generate_random_color():
    """Generate random RGB values."""
    return [random.randint(0, 255) for _ in range(3)]

def adjust_brightness(color, velocity):
    """Adjust color brightness based on velocity."""
    brightness_scale = velocity / 127  # Normalize velocity to a range of 0-1
    return [int(c * brightness_scale) for c in color]

def add_fade_out(led_index):
    """Add an LED to the fading dictionary for processing."""
    current_color = strip.getPixelColor(led_index)
    r = (current_color >> 16) & 0xFF
    g = (current_color >> 8) & 0xFF
    b = current_color & 0xFF
    fading_leds[led_index] = [r, g, b, 50]  # 50 steps for 500ms fade-out

def fade_loop():
    """Continuously fade out LEDs in parallel."""
    while True:
        if fading_leds:
            for led_index, (r, g, b, steps_remaining) in list(fading_leds.items()):
                if steps_remaining > 0:
                    factor = steps_remaining / 50  # Fade factor (1 to 0)
                    set_led_color(led_index, [int(r * factor), int(g * factor), int(b * factor)])
                    fading_leds[led_index][3] -= 1  # Decrement steps
                else:
                    fading_leds.pop(led_index)  # Remove LED when fade is complete
            strip.show()  # Update all LEDs at once
        time.sleep(0.01)  # 10ms interval

def handle_midi_event(event_line):
    """Process a single MIDI event."""
    global sustain_active, active_notes

    print(f"Received MIDI event: {event_line.strip()}")  # Log the MIDI event

    if "Note on" in event_line:
        parts = event_line.split(",")
        note = int(parts[1].split()[1])
        velocity = int(parts[2].split()[1])
        led_index = (note - BASE_NOTE) * 2  # Map each note to two LEDs
        if 0 <= led_index < NUM_LEDS and velocity > 0:
            base_color = generate_random_color()
            color = adjust_brightness(base_color, velocity)
            set_led_color(led_index, color)
            set_led_color(led_index + 1, color)  # Light up the second LED
            strip.show()  # Apply changes
            active_notes.add(note)  # Track the active note
    elif "Note off" in event_line:
        parts = event_line.split(",")
        note = int(parts[1].split()[1])
        led_index = (note - BASE_NOTE) * 2  # Map each note to two LEDs
        if note in active_notes:
            if not sustain_active:  # Only turn off LEDs if sustain is not active
                active_notes.remove(note)
                if 0 <= led_index < NUM_LEDS:
                    add_fade_out(led_index)
                    add_fade_out(led_index + 1)
    elif "Control change" in event_line:
        parts = event_line.split(",")
        controller = int(parts[1].split()[1])
        value = int(parts[2].split()[1])
        if controller == 64:  # Sustain pedal (Controller 64)
            sustain_active = value >= 64  # Sustain is active when value is 64 or higher
            if not sustain_active:
                # Turn off all LEDs for released notes when sustain is deactivated
                for note in list(active_notes):
                    led_index = (note - BASE_NOTE) * 2
                    if 0 <= led_index < NUM_LEDS:
                        add_fade_out(led_index)
                        add_fade_out(led_index + 1)
                active_notes.clear()

def listen_to_midi():
    """Listen to MIDI events using aseqdump."""
    process = subprocess.Popen(
        ["aseqdump", "--port", MIDI_PORT],
        stdout=subprocess.PIPE,
        text=True
    )
    while True:
        line = process.stdout.readline()
        if line and ("Note" in line or "Control change" in line):
            handle_midi_event(line)

# Start the fade loop in a separate thread
fade_thread = threading.Thread(target=fade_loop, daemon=True)
fade_thread.start()

# Start listening to MIDI events
midi_thread = threading.Thread(target=listen_to_midi, daemon=True)
midi_thread.start()

print("Listening for MIDI events. Press Ctrl+C to exit.")
try:
    midi_thread.join()
except KeyboardInterrupt:
    print("Exiting.")
    # Turn off all LEDs before exiting
    for i in range(NUM_LEDS):
        set_led_color(i, [0, 0, 0])
    strip.show()
