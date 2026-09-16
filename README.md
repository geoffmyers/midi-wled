# MIDI WLED - Piano LED Visualizer

<!-- BADGES:START -->
![mido 1.3.3](https://img.shields.io/badge/mido-1.3.3-306998?style=flat-square)
[![Licence GPL--2.0](https://img.shields.io/badge/licence-GPL--2.0-blue?style=flat-square)](LICENSE.md)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square)](CONTRIBUTING.md)
<!-- BADGES:END -->

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

## Hardware Requirements

- Raspberry Pi (any model with GPIO)
- WS2815 LED strip (144 LEDs)
- USB MIDI keyboard or controller
- LED strip connected to GPIO pin 18 (PWM0)

## Installation

```bash
# Run the setup script (installs Python 3, creates venv, installs deps)
./configure-python.sh

# Or manually:
sudo apt-get install python3 python3-pip python3-venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Dependencies

- Python 3.9+
- [mido](https://mido.readthedocs.io/) 1.3.3 - MIDI library
- [rpi-ws281x](https://github.com/rpi-ws281x/rpi-ws281x-python) 5.0.0 - LED strip control
- [python-rtmidi](https://github.com/SpotlightKid/python-rtmidi) 1.5.8 - MIDI I/O backend
- `aseqdump` (ALSA utils) - required by `piano-lights.py`

## Usage

```bash
# Real-time piano lights (requires sudo for GPIO access)
sudo venv/bin/python piano-lights.py

# Play a MIDI file with synchronized LEDs
sudo venv/bin/python play-song.py midi/song.mid

# Play with options
sudo venv/bin/python play-song.py midi/song.mid --repeat --speed-percent 75 --fade --ascii

# Learn a song interactively (waits for you to play each note)
sudo venv/bin/python learn-song.py midi/song.mid

# List available MIDI ports
venv/bin/python list-midi-ports.py

# Start piano-lights as a background tmux session
./start-tmux.sh
```

### play-song.py Options

| Flag | Description |
|------|-------------|
| `--max-velocity` | Play all notes at maximum velocity (127) |
| `--piano-only` | Play only piano instrument notes |
| `--bpm N` | Override playback tempo |
| `--repeat` | Loop playback continuously |
| `--speed-percent N` | Play at N% of original speed (e.g., 50 for half speed) |
| `--force-piano` | Force all instruments to acoustic grand piano |
| `--ascii` | Enable ASCII terminal visualization |
| `--fade` | Enable LED fade effect on note release |

## Configuration

Edit constants at the top of each Python script:

| Setting | Default | Description |
|---------|---------|-------------|
| `GPIO_PIN` | 18 | GPIO pin for LED data line |
| `NUM_LEDS` | 144 | Total LEDs on the strip |
| `BASE_NOTE` | 29 | MIDI note mapped to first LED |
| `MIDI_PORT` | `20:0` | ALSA MIDI port (`piano-lights.py`) |
| `MIDI_OUTPUT_PORT` | `CH345:CH345 MIDI 1 20:0` | MIDI output port name |

## Scripts

| Script | Description |
|--------|-------------|
| `piano-lights.py` | Real-time MIDI input listener via `aseqdump` |
| `play-song.py` | MIDI file player with LED sync and audio output |
| `learn-song.py` | Interactive mode - plays MIDI and waits for correct note input |
| `list-midi-ports.py` | Lists available MIDI input/output ports |
| `configure-python.sh` | Sets up Python venv and installs dependencies |
| `start-tmux.sh` | Launches `piano-lights.py` in a detached tmux session |

## Notes

- Must run with `sudo` because `rpi_ws281x` requires root access to GPIO pins.
- `MIDI_PORT` and `MIDI_OUTPUT_PORT` values are hardware-specific and must match your USB MIDI device.
- GPIO pin 18 (PWM0) conflicts with onboard audio on Raspberry Pi.
- Each MIDI note maps to 2 consecutive LEDs.

## Credits

MIDI I/O by [mido](https://mido.readthedocs.io/) and
[python-rtmidi](https://spotlightkid.github.io/python-rtmidi/). LED output
driven by [rpi-ws281x](https://github.com/rpi-ws281x/rpi-ws281x-python).

Interoperates with [WLED](https://kno.wled.ge/), which is an independent
project and not affiliated with this one.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for how the project fits together — the
layout, the data flow, and the constraints worth knowing before changing it.

## Contributing

Bug reports and pull requests are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md)
for setup, checks and how this repository is published.

## License

This project is licensed under the GNU General Public License v2.0. See [LICENSE.md](LICENSE.md) for details.
