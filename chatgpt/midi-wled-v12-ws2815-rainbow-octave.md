---
title: Configuration
created: 2026-01-28
modified: 2026-01-28
description: "GPIO_PIN = 18  # GPIO pin connected to the LEDs (PWM pin, use 18 for Raspberry Pi) NUM_LEDS = 144  # Total LEDs on the WS2815 strip LED_FREQ_HZ = 800000  # LED signal frequency in hertz (800kHz for..."
tags: [music]
---

Modify the script so that each octave is mapped to the full color spectrum (e.g. all "C" notes are red).

---

To map each octave to the full color spectrum, the script needs to calculate the color for a note based on its position within the octave, regardless of its absolute pitch. This way, all "C" notes are the same color (e.g., red), "C#" notes are slightly shifted in the spectrum, and so on.

Here’s the updated script with the modification:

```python
import threading
import subprocess
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
MIDI_PORT = "20:0"  # Update with your aseqdump port

# State variables
sustain_active = False
active_notes = set()

# Initialize the LED strip
strip = PixelStrip(NUM_LEDS, GPIO_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

def set_led_color(led_index, color):
    """Set the color of a specific LED on the strip."""
    if 0 <= led_index < NUM_LEDS:
        strip.setPixelColor(led_index, Color(*color))  # Convert to GRB for WS2815
        strip.show()

def generate_octave_color(note):
    """Generate a color based on the note's position within its octave."""
    notes_in_octave = 12  # Total notes in an octave
    note_in_octave = (note - BASE_NOTE) % notes_in_octave  # Position within the octave
    hue = note_in_octave / notes_in_octave  # Normalize to a range of 0-1
    r, g, b = hsv_to_rgb(hue, 1.0, 1.0)  # Full saturation and brightness
    return [int(r * 255), int(g * 255), int(b * 255)]

def adjust_brightness(color, velocity):
    """Adjust color brightness based on velocity."""
    brightness_scale = velocity / 127  # Normalize velocity to a range of 0-1
    return [int(c * brightness_scale) for c in color]

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
            base_color = generate_octave_color(note)
            color = adjust_brightness(base_color, velocity)
            set_led_color(led_index, color)
            set_led_color(led_index + 1, color)  # Light up the second LED
            active_notes.add(note)  # Track the active note
    elif "Note off" in event_line:
        parts = event_line.split(",")
        note = int(parts[1].split()[1])
        led_index = (note - BASE_NOTE) * 2  # Map each note to two LEDs
        if note in active_notes:
            if not sustain_active:  # Only turn off LEDs if sustain is not active
                active_notes.remove(note)
                if 0 <= led_index < NUM_LEDS:
                    set_led_color(led_index, [0, 0, 0])  # Turn off the first LED
                    set_led_color(led_index + 1, [0, 0, 0])  # Turn off the second LED
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
                        set_led_color(led_index, [0, 0, 0])
                        set_led_color(led_index + 1, [0, 0, 0])
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
```

### Key Modifications:

1. **New `generate_octave_color` Function**:

   - Determines the note's position within its octave (`note_in_octave`).
   - Maps the position to a hue value spanning the full spectrum (red to red across 12 notes).

2. **Color Mapping by Octave**:

   - All "C" notes are the same color (red).
   - "C#" is shifted slightly along the spectrum, continuing through the octave.

3. **HSV to RGB Conversion**:
   - Smoothly transitions colors across the octave using the HSV color model.

Now, each octave cycles through the full color spectrum, creating a consistent mapping where notes within the same pitch class (e.g., "C") share the same color regardless of octave.
