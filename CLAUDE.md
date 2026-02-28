---
title: CLAUDE.md - MIDI WLED
created: 2026-02-06
modified: 2026-02-06
description: "A Raspberry Pi project that maps MIDI piano input to a WS2815 LED strip (144 LEDs) for real-time piano key visualization. Includes live performance lighting, MIDI file playback with synchronized..."
tags: [music, claude]
---

# CLAUDE.md - MIDI WLED

## Project Overview

A Raspberry Pi project that maps MIDI piano input to a WS2815 LED strip (144 LEDs) for real-time piano key visualization. Includes live performance lighting, MIDI file playback with synchronized LEDs, and an interactive learn-a-song mode.

## Architecture / Key Files

- `piano-lights.py` - Real-time MIDI input listener; maps note-on/off events to LED colors via `aseqdump`
- `play-song.py` - MIDI file player with synchronized LED visualization and audio output; supports speed/tempo/repeat/fade options
- `learn-song.py` - Interactive mode that plays a MIDI file and waits for the user to play each correct note before advancing
- `list-midi-ports.py` - Utility to list available MIDI input/output ports via `mido`
- `configure-python.sh` - Sets up Python 3 venv and installs dependencies
- `start-tmux.sh` - Launches `piano-lights.py` in a detached tmux session (for autostart)
- `requirements.txt` - Python dependencies: `mido`, `rpi-ws281x`, `python-rtmidi`
- `midi/` - MIDI file collection (32 files)
- `chatgpt/` - ChatGPT conversation exports used during development
- `old/` - Previous script versions
- `.github/` - GitHub Actions workflows

## Development Commands

```bash
# Initial setup on Raspberry Pi
./configure-python.sh

# Activate virtual environment
source venv/bin/activate

# Run real-time piano lights
sudo venv/bin/python piano-lights.py

# Play a MIDI file with LEDs
sudo venv/bin/python play-song.py midi/song.mid

# Play with options
sudo venv/bin/python play-song.py midi/song.mid --repeat --speed-percent 75 --fade --ascii

# Learn a song interactively
sudo venv/bin/python learn-song.py midi/song.mid

# List MIDI ports
venv/bin/python list-midi-ports.py

# Start as background service via tmux
./start-tmux.sh
```

## Common Tasks

- **Change MIDI port**: Edit `MIDI_PORT` in `piano-lights.py` or `MIDI_OUTPUT_PORT` / `MIDI_INPUT_PORT` in other scripts
- **Adjust LED mapping**: Modify `BASE_NOTE` (default 29) and the `* 2` multiplier (2 LEDs per note)
- **Change LED count**: Edit `NUM_LEDS` (default 144) across scripts
- **Add MIDI files**: Place `.mid` files in the `midi/` directory

## Gotchas

- Must run with `sudo` because `rpi_ws281x` requires root access to the GPIO pins
- The `MIDI_PORT` and `MIDI_OUTPUT_PORT` values are hardware-specific and must match your USB MIDI device
- `piano-lights.py` uses `aseqdump` (ALSA sequencer) while `play-song.py` uses `mido`'s `open_output`
- LED strip uses GPIO pin 18 (PWM0) -- this conflicts with onboard audio on Raspberry Pi
- Each MIDI note maps to 2 consecutive LEDs; `BASE_NOTE = 29` means MIDI note 29 is LED index 0
- Colors are generated using HSV color wheel based on note position within the octave
- This is a git subtree; push changes upstream with `git subtree push --prefix=music/midi-wled midi-wled main`
