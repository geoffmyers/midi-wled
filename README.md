---
title: MIDI WLED - Piano LED Visualizer
created: 2026-02-06
modified: 2026-02-06
description: "A Raspberry Pi project that connects a MIDI keyboard to a WS2815 LED strip, creating real-time piano key visualizations. Notes light up with octave-based colors and velocity-based brightness. Also..."
tags: [music, readme]
---

# MIDI WLED - Piano LED Visualizer

## Overview

A Raspberry Pi project that connects a MIDI keyboard to a WS2815 LED strip, creating real-time piano key visualizations. Notes light up with octave-based colors and velocity-based brightness. Also supports MIDI file playback with synchronized LEDs and an interactive song-learning mode.

## Features

- Real-time MIDI input to LED color mapping (144 LEDs, 2 per key)
- Octave-based HSV color scheme (each octave cycles the color wheel)
- Velocity-sensitive brightness
- Sustain pedal support
- MIDI file playback with synchronized LED visualization
- Adjustable playback speed, tempo, and repeat options
- LED fade effect on note release
- ASCII terminal visualization mode
- Interactive learn-a-song mode (waits for correct note input)
- Force-piano mode (all instruments play as piano)
- Background startup via tmux

## Installation / Setup

### Hardware

- Raspberry Pi (any model with GPIO)
- WS2815 LED strip (144 LEDs)
- USB MIDI keyboard or controller
- LED strip connected to GPIO pin 18 (PWM0)

### Software

```bash
# Run the setup script
./configure-python.sh

# Or manually:
sudo apt-get install python3 python3-pip python3-venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Edit constants at the top of each Python script:

| Setting | Default | Description |
|---------|---------|-------------|
| `GPIO_PIN` | 18 | GPIO pin for LED data line |
| `NUM_LEDS` | 144 | Total LEDs on the strip |
| `BASE_NOTE` | 29 | MIDI note mapped to first LED |
| `MIDI_PORT` | `20:0` | ALSA MIDI port (piano-lights.py) |
| `MIDI_OUTPUT_PORT` | `CH345:CH345 MIDI 1 20:0` | MIDI output port name |

## Usage

```bash
# Real-time piano lights (requires sudo for GPIO)
sudo venv/bin/python piano-lights.py

# Play a MIDI file
sudo venv/bin/python play-song.py midi/song.mid

# Play with options
sudo venv/bin/python play-song.py midi/song.mid --repeat --speed-percent 75 --fade --ascii

# Learn a song
sudo venv/bin/python learn-song.py midi/song.mid

# List available MIDI ports
venv/bin/python list-midi-ports.py

# Start as background service
./start-tmux.sh
```

## Requirements

- Python 3.9+
- `mido` 1.3.3 (MIDI library)
- `rpi-ws281x` 5.0.0 (LED strip control)
- `python-rtmidi` 1.5.8 (MIDI I/O)
- `aseqdump` (ALSA utils, for piano-lights.py)

## License

This project is licensed under the GNU General Public License v2.0 - see the [LICENSE.md](LICENSE.md) file for details.
