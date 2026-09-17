<p align="center">
  <img src="docs/icon.svg" width="96" height="96" alt="MIDI WLED icon">
</p>

# MIDI WLED - Piano LED Visualizer

<!-- BADGES:START -->
![mido 1.3.3](https://img.shields.io/badge/mido-1.3.3-306998?style=flat-square)
[![Licence GPL-3.0-or-later](https://img.shields.io/badge/licence-GPL--3.0--or--later-blue?style=flat-square)](LICENSE.md)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square)](CONTRIBUTING.md)
<!-- BADGES:END -->

## Table of Contents

- [Description](#description)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
  - [Live lights](#live-lights)
  - [Getting MIDI files](#getting-midi-files)
  - [Playing a MIDI file](#playing-a-midi-file)
  - [Learning a song](#learning-a-song)
  - [Finding your MIDI ports](#finding-your-midi-ports)
- [Configuration](#configuration)
- [Testing](#testing)
- [Architecture](#architecture)
- [Credits](#credits)
- [Contributing](#contributing)
- [License](#license)

## Description

A set of Python scripts for a Raspberry Pi that turns a WS2815 LED strip into a
light bar for a piano. Each key you play lights two LEDs, coloured by its place
in the octave and as bright as you played it. The same strip can follow a MIDI
file while it plays through your instrument, or run a song one note at a time
and wait for you to play each one.

Despite the name, the project does **not** use [WLED](https://kno.wled.ge/). The
scripts drive the strip directly from the Pi's GPIO through `rpi-ws281x`.

## Features

- **Live key lighting.** Each note lights two LEDs as you play it.
- **Colour by pitch.** The hue cycles through the colour wheel once per octave,
  so every C is the same colour.
- **Velocity-sensitive brightness.** A soft note glows dimly and a hard one
  shines at full brightness.
- **Sustain pedal support** in live mode: held notes stay lit until the pedal
  (MIDI CC 64) is released.
- **MIDI file playback** through your instrument with the strip in sync,
  including tempo override, speed percentage, repeat, full velocity, piano-only
  and all-piano options, and a fade-out on note release. Each part keeps its own
  instrument sound. Drum-channel notes are skipped.
- **A terminal view.** `--ascii` draws the active notes across an 88-key row in
  24-bit colour while a file plays.
- **Learn-a-song mode** that pauses after every note until you play it, skipping
  the drum channel.
- **Works with any Standard MIDI File** you supply. The repository ships
  none; see [Getting MIDI files](#getting-midi-files).
- **Headless start-up** in a detached `tmux` session.

## Requirements

**Hardware**

- A Raspberry Pi with a GPIO header
- A WS2815 addressable LED strip with 144 LEDs, and a 12 V supply for it (the
  WS2815 is a 12 V part)
- The strip's data line on **GPIO 18** (PWM0)
- A USB MIDI keyboard or MIDI interface. The defaults assume a CH345-based USB
  MIDI cable.

**Software**

- Raspberry Pi OS (or another Debian-based system) with Python 3.9 or newer
- `aseqdump` from `alsa-utils`, used by the live-lights script
- `tmux`, only for `start-tmux.sh`
- Root access: `rpi-ws281x` needs it to drive the GPIO pin, so the LED scripts
  run under `sudo`
- Onboard analogue audio turned off, since it shares PWM0 with the strip

The Python dependencies are pinned in `requirements.txt`: `mido`,
`python-rtmidi` and `rpi-ws281x`.

## Installation

```bash
git clone https://github.com/geoffmyers/midi-wled.git
cd midi-wled

# System packages (configure-python.sh does not install these two)
sudo apt-get install alsa-utils tmux

# Python 3, a virtual environment in ./venv, and the pinned dependencies
./configure-python.sh
```

`configure-python.sh` is the same as doing it by hand:

```bash
sudo apt-get install python3 python3-pip python3-venv
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

Then set your MIDI port names (see [Configuration](#configuration)).

## Usage

All of the LED scripts run as root, from the project directory.

### Live lights

```bash
sudo venv/bin/python piano-lights.py
```

This listens to your keyboard through `aseqdump` and lights the strip as you
play. Press **Ctrl+C** to stop; the strip is cleared on exit.

To keep it running after you log out:

```bash
./start-tmux.sh      # starts a detached tmux session called "piano-lights"
tmux attach -t piano-lights
```

### Getting MIDI files

No songs are included: a MIDI file is someone's arrangement, and most songs are
also under copyright, so each file needs a licence that lets you use it. The
[Mutopia Project](https://www.mutopiaproject.org/) publishes free MIDI files of
public-domain music, each with its licence stated. Put your files anywhere; the
examples below use a `midi/` folder in the project directory:

```bash
mkdir -p midi
cp ~/Downloads/fur-elise.mid midi/
```

### Playing a MIDI file

```bash
sudo venv/bin/python play-song.py midi/fur-elise.mid
sudo venv/bin/python play-song.py midi/fur-elise.mid --speed-percent 75 --fade --ascii
```

The script prints the file's tracks, instruments, note count, duration, tempo
and key, then sends the notes to your MIDI output port while lighting the strip.

| Flag | Effect |
|---|---|
| `--max-velocity` | Send and light every note at full velocity (127) |
| `--bpm N` | Play at N beats per minute; later tempo changes in the file keep their proportions |
| `--speed-percent N` | Play at N% of the original speed, e.g. `50` for half speed |
| `--repeat` | Loop the file |
| `--ascii` | Draw the active notes in the terminal |
| `--fade` | Fade LEDs out on note release instead of switching them off |
| `--piano-only` | Play only the parts set to a piano sound (General MIDI programs 1–8); the rest stay silent and dark |
| `--force-piano` | Switch every part to acoustic grand piano |

The file's program changes are sent to your instrument, so on a General MIDI
instrument each part plays with the sound the file asks for. Notes on the drum
channel (MIDI channel 10) are never sent.

### Learning a song

```bash
sudo venv/bin/python learn-song.py midi/twinkle-twinkle-little-star.mid
```

Each note lights up and is sent to your instrument, and playback waits until you
play that note on the keyboard. A wrong note is reported and the song keeps
waiting. Drum-channel notes are skipped.

### Finding your MIDI ports

```bash
venv/bin/python list-midi-ports.py   # port names for mido (play-song, learn-song)
./dump-midi-in.sh                    # raw events from ALSA port 20
aseqdump -l                          # ALSA port numbers (piano-lights)
```

## Configuration

The LED/GPIO constants and the note-to-LED mapping live in one shared module,
`led_piano.py`, imported by all three scripts below — edit them once. Each
script keeps its own MIDI port name(s), since those are specific to its role.

| Constant | Default | Lives in | Meaning |
|---|---|---|---|
| `GPIO_PIN` | `18` | `led_piano.py` | GPIO pin for the strip's data line |
| `NUM_LEDS` | `144` | `led_piano.py` | LEDs on the strip |
| `LED_BRIGHTNESS` | `255` | `led_piano.py` | Overall brightness, 0–255 |
| `BASE_NOTE` | `29` | `led_piano.py` | MIDI note lit by the first LED |
| `MIDI_PORT` | `20:0` | `piano-lights.py` | ALSA port passed to `aseqdump` |
| `MIDI_OUTPUT_PORT` | `CH345:CH345 MIDI 1 20:0` | `play-song.py`, `learn-song.py` | mido output port for your instrument |
| `MIDI_INPUT_PORT` | `CH345:CH345 MIDI 1 20:0` | `learn-song.py` | mido input port for your keyboard |

Each note lights LEDs `(note − BASE_NOTE) × 2` and the one after it. With the
defaults, the 144 LEDs cover 72 notes, from MIDI note 29 (F1) to note 100 (E7).
Notes outside that range are ignored.

## Testing

`led_piano.py` and the pure logic in each script (the note-to-LED mapping,
colour and brightness math, `play-song.py`'s `adjust_tempo()`, and the
note-on/note-off dispatch) have pytest unit tests that run on any machine —
no Raspberry Pi or LED strip required. `rpi_ws281x` is a hardware extension
that only builds against a Pi's GPIO/DMA headers, so the tests install a fake
in its place (see `tests/conftest.py`) rather than depending on it.
`requirements-dev.txt` pins everything the suite actually imports (including
`mido`, for the real `MidiFile`/`MidiTrack` fixtures in
`test_play_song.py`), so one install works whether or not `requirements.txt`
is already on the machine:

```bash
python3 -m venv venv
venv/bin/pip install -r requirements-dev.txt
venv/bin/python -m pytest tests/ -v
```

## Architecture

Three independent scripts share one idea, a note-to-LED mapping, through one
shared module, `led_piano.py`:

```
USB MIDI keyboard ──► aseqdump ──► piano-lights.py ──┐
                                                    ├──► led_piano.LedStrip ──► rpi-ws281x ──► GPIO 18 ──► WS2815 strip
MIDI file ──► mido ──► play-song.py / learn-song.py ─┘
                          │
                          └──► mido output ──► your instrument
                   (learn-song.py also reads the keyboard through mido)
```

| Path | Role |
|---|---|
| `led_piano.py` | Shared LED/GPIO constants, note-to-LED mapping, colour and brightness math, and the thread-safe `LedStrip` wrapper |
| `piano-lights.py` | Live mode: parses `aseqdump` output line by line, with sustain-pedal handling |
| `play-song.py` | File playback with tempo, speed, repeat, fade and terminal-view options |
| `learn-song.py` | Plays a file and blocks on each note until the keyboard sends it |
| `list-midi-ports.py`, `dump-midi-in.sh` | Diagnostics for finding the right ports |
| `configure-python.sh`, `start-tmux.sh` | Setup and a background session |
| `midi/` | Where the examples keep your MIDI files; none are included |

See [ARCHITECTURE.md](ARCHITECTURE.md) for more on the mapping and the
constraints of driving the strip.

## Credits

- MIDI I/O by [mido](https://mido.readthedocs.io/) and
  [python-rtmidi](https://spotlightkid.github.io/python-rtmidi/); live input
  through `aseqdump` from [alsa-utils](https://github.com/alsa-project/alsa-utils).
- LED output by [rpi-ws281x](https://github.com/rpi-ws281x/rpi-ws281x-python).
- [WLED](https://kno.wled.ge/) is an independent project. Despite this
  repository's name it is not used here, and it is not affiliated with this
  project.
- The README icon is the [Font Awesome](https://fontawesome.com/) `lightbulb` glyph,
  used under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Written by Geoff Myers.

## Contributing

Bug reports and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md)
for setup, checks and how this repository is published.

## License

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See [LICENSE.md](LICENSE.md) for the full text of the GNU
General Public License.

SPDX-License-Identifier: `GPL-3.0-or-later`
