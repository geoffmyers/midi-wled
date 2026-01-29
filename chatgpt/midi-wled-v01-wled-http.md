Write a Python script that reads MIDI events as input, maps each keyboard note to an individual RGB LED, and uses the WLED JSON API to sync the RGB LED lights with the keyboard. Here is an example of the MIDI input:

```aseqdump --port=20
Waiting for data. Press Ctrl+C to end.
Source Event Ch Data
20:0 Note on 0, note 48, velocity 65
20:0 Note off 0, note 48, velocity 64
20:0 Note on 0, note 50, velocity 77
20:0 Note off 0, note 50, velocity 64
20:0 Note on 0, note 52, velocity 71
20:0 Note off 0, note 52, velocity 64
20:0 Note on 0, note 53, velocity 88
20:0 Note off 0, note 53, velocity 64
20:0 Note on 0, note 55, velocity 70
20:0 Note off 0, note 55, velocity 64
20:0 Note on 0, note 57, velocity 82
20:0 Note off 0, note 57, velocity 64
20:0 Note on 0, note 59, velocity 77
20:0 Note off 0, note 59, velocity 64
20:0 Note on 0, note 60, velocity 73
20:0 Note off 0, note 60, velocity 64
```

The WLED JSON API documentation is included in the attached HTML file.

---

Here's a Python script that integrates the MIDI keyboard with RGB LEDs using the WLED JSON API. The script listens to MIDI events, maps each note to an LED, and sends color updates to the WLED device.

### Script

```python
import subprocess
import json
import requests
import threading

# Configuration
WLED_IP = "192.168.1.100"  # Replace with your WLED device IP address
NUM_LEDS = 88  # Total LEDs to match piano keys
BASE_NOTE = 21  # MIDI note number for A0
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
```

### Key Features:

1. **MIDI Listening**: Uses `aseqdump` to capture MIDI events.
2. **LED Mapping**: Maps MIDI notes to LED indices based on the keyboard range.
3. **WLED Integration**: Sends RGB values to the WLED device using the JSON API.
4. **Velocity to Color**: Converts MIDI velocity to a gradient color.

### Requirements:

- Python 3.x
- `requests` module: Install via `pip install requests`
- WLED device running with accessible IP.
- `aseqdump` installed on the system.

### Usage:

1. Replace `WLED_IP` with the IP address of your WLED device.
2. Update `MIDI_PORT` with the correct port for `aseqdump`.
3. Run the script, and it will start synchronizing MIDI input with the RGB LEDs.
