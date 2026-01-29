import subprocess
import json
import requests
import threading

# Configuration
WLED_IP = "10.0.10.142"  # Replace with your WLED device IP address
NUM_LEDS = 50  # Total LEDs to match piano keys
BASE_NOTE = 40  # MIDI note number for E2
MIDI_PORT = "20:0"  # Update with your aseqdump port

def send_to_wled(led_index, color):
    """Send a color update to WLED."""
    url = f"http://{WLED_IP}/json/state"
    payload = {
        "seg": [{
            "i": [led_index, led_index, color]
        }]
    }
    headers = {"Content-Type": "application/json"}
    try:
        requests.post(url, data=json.dumps(payload), headers=headers)
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with WLED: {e}")

def map_velocity_to_color(velocity):
    """Convert MIDI velocity to RGB color."""
    intensity = int((velocity / 127) * 255)
    return [intensity, 0, 255 - intensity]  # Gradient from blue to red

def handle_midi_event(event_line):
    """Process a single MIDI event."""
    if "Note on" in event_line:
        parts = event_line.split(",")
        note = int(parts[1].split()[1])
        velocity = int(parts[2].split()[1])
        led_index = note - BASE_NOTE
        if 0 <= led_index < NUM_LEDS and velocity > 0:
            color = map_velocity_to_color(velocity)
            send_to_wled(led_index, color)
    elif "Note off" in event_line:
        parts = event_line.split(",")
        note = int(parts[1].split()[1])
        led_index = note - BASE_NOTE
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
thread = threading.Thread(target=listen_to_midi, daemon=True)
thread.start()

print("Listening for MIDI events. Press Ctrl+C to exit.")
try:
    thread.join()
except KeyboardInterrupt:
    print("Exiting.")
