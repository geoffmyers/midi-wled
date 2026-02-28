---
title: Configuration
created: 2026-01-28
modified: 2026-01-28
description: "WLED_IP = \"10.0.10.142\"  # Replace with your WLED device IP address WLED_PORT = 21324  # Default UDP port for WLED realtime protocol NUM_LEDS = 44  # Total LEDs (88 keys / 2) BASE_NOTE = 40  # MIDI..."
tags: [music]
---

Modify the following Python script so that instead of a 1-to-1 mapping of piano keys to LED lights, there is a 1-to-2 mapping of piano keys to LED lights (88 keys mapped to 44 lights):

[...]

---

To implement a 1-to-2 mapping (88 piano keys to 44 LEDs), we need to adjust how the `led_index` is calculated. Each LED will represent two consecutive keys, so we'll divide the key number by 2 to determine the corresponding LED index. Here's the modified script:

```python
import subprocess
import socket
import threading
import random

# Configuration
WLED_IP = "10.0.10.142"  # Replace with your WLED device IP address
WLED_PORT = 21324  # Default UDP port for WLED realtime protocol
NUM_LEDS = 44  # Total LEDs (88 keys / 2)
BASE_NOTE = 40  # MIDI note number for A0
MIDI_PORT = "20:0"  # Update with your aseqdump port
UDP_TIMEOUT = 2  # Timeout in seconds for WLED to revert to normal mode

# Create a UDP socket
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_to_wled(led_index, color):
    """Send a color update to WLED using the WARLS protocol."""
    if not (0 <= led_index < NUM_LEDS):
        return

    # Construct the packet
    packet = bytearray([1, UDP_TIMEOUT])  # WARLS protocol, timeout
    packet.extend([led_index, *color])  # LED index and RGB color

    try:
        udp_socket.sendto(packet, (WLED_IP, WLED_PORT))
    except socket.error as e:
        print(f"Error sending UDP packet: {e}")

def generate_random_color():
    """Generate random RGB values."""
    return [random.randint(0, 255) for _ in range(3)]

def adjust_brightness(color, velocity):
    """Adjust color brightness based on velocity."""
    brightness_scale = velocity / 127  # Normalize velocity to a range of 0-1
    return [int(c * brightness_scale) for c in color]

def handle_midi_event(event_line):
    """Process a single MIDI event."""
    print(f"Received MIDI event: {event_line.strip()}")  # Log the MIDI event

    if "Note on" in event_line:
        parts = event_line.split(",")
        note = int(parts[1].split()[1])
        velocity = int(parts[2].split()[1])
        led_index = (note - BASE_NOTE) // 2  # Map two keys to one LED
        if 0 <= led_index < NUM_LEDS and velocity > 0:
            base_color = generate_random_color()
            color = adjust_brightness(base_color, velocity)
            send_to_wled(led_index, color)
    elif "Note off" in event_line:
        parts = event_line.split(",")
        note = int(parts[1].split()[1])
        led_index = (note - BASE_NOTE) // 2  # Map two keys to one LED
        if 0 <= led_index < NUM_LEDS:
            send_to_wled(led_index, [0, 0, 0])  # Turn off the LED

def listen_to_midi():
    """Listen to MIDI events using aseqdump."""
    process = subprocess.Popen(
        ["aseqdump", "--port", MIDI_PORT],
        stdout=subprocess.PIPE,
        text=True
    )
    while True:
        line = process.stdout.readline()
        if line and "Note" in line:
            handle_midi_event(line)

# Start listening to MIDI events
midi_thread = threading.Thread(target=listen_to_midi, daemon=True)
midi_thread.start()

print("Listening for MIDI events. Press Ctrl+C to exit.")
try:
    midi_thread.join()
except KeyboardInterrupt:
    print("Exiting.")
    udp_socket.close()
```

### Key Changes:

1. **Updated `NUM_LEDS`:** Set to 44 to reflect the 1-to-2 mapping.
2. **Adjusted `led_index`:** `led_index = (note - BASE_NOTE) // 2` ensures each LED corresponds to two keys.
3. **Logic for note on/off events:** This mapping ensures all key presses update the correct LED while adhering to the new mapping.

This modification assumes that BASE_NOTE (A0) is properly aligned with the start of the keys to allow clean division into groups of two keys per LED.
