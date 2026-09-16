# MIDI WLED - Piano LED Visualizer

<!-- BADGES:START -->
![mido 1.3.3](https://img.shields.io/badge/mido-1.3.3-306998?style=flat-square)
[![Licence GPL--2.0](https://img.shields.io/badge/licence-GPL--2.0-blue?style=flat-square)](LICENSE.md)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square)](CONTRIBUTING.md)
<!-- BADGES:END -->

## Description

A set of Python scripts for a Raspberry Pi that turns a WS2815 LED strip into a
light bar for a piano. Each key you play lights two LEDs, coloured by its place
in the octave and as bright as you played it. The same strip can follow a MIDI
file while it plays through your instrument, or run a song one note at a time
and wait for you to play each one.

Despite the name, the project does **not** use [WLED](https://kno.wled.ge/). The
scripts drive the strip directly from the Pi's GPIO through `rpi-ws281x`.

## Table of Contents

- [Description](#description)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
  - [Live lights](#live-lights)
  - [Playing a MIDI file](#playing-a-midi-file)
  - [Learning a song](#learning-a-song)
  - [Finding your MIDI ports](#finding-your-midi-ports)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Credits](#credits)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Live key lighting.** Each note lights two LEDs as you play it.
- **Colour by pitch.** The hue cycles through the colour wheel once per octave,
  so every C is the same colour.
- **Velocity-sensitive brightness.** A soft note glows dimly and a hard one
  shines at full brightness.
- **Sustain pedal support** in live mode: held notes stay lit until the pedal
  (MIDI CC 64) is released.
- **MIDI file playback** through your instrument with the strip in sync,
  including tempo override, speed percentage, repeat and a fade-out on note
  release. Drum-channel notes are skipped.
- **A terminal view.** `--ascii` draws the active notes across an 88-key row in
  24-bit colour while a file plays.
- **Learn-a-song mode** that pauses after every note until you play it, skipping
  the drum channel.
- **32 MIDI files included** in `midi/`, from *Für Elise* to *Super Mario Bros.*
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

### Playing a MIDI file

```bash
sudo venv/bin/python play-song.py midi/fur-elise.mid
sudo venv/bin/python play-song.py midi/fur-elise.mid --speed-percent 75 --fade --ascii
```

The script prints the file's tracks, instruments, note count, duration, tempo
and key, then sends the notes to your MIDI output port while lighting the strip.

| Flag | Effect |
|---|---|
| `--max-velocity` | Play every note at full velocity (127) |
| `--bpm N` | Play at N beats per minute |
| `--speed-percent N` | Play at N% of the original speed, e.g. `50` for half speed |
| `--repeat` | Loop the file |
| `--ascii` | Draw the active notes in the terminal |
| `--fade` | Fade LEDs out on note release instead of switching them off |
| `--piano-only` | Meant to drop non-piano program changes. **No audible effect yet** (see below) |
| `--force-piano` | Meant to switch every part to acoustic grand piano. **No audible effect yet** (see below) |

**Known issue:** `play-song.py` forwards only note messages to the output port,
never program changes, so your instrument plays every part with whatever sound
it already has selected. That is why `--piano-only` and `--force-piano`
currently change nothing. Notes on the drum channel (MIDI channel 10) are never
sent.

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

Settings are constants at the top of each script. Edit them in every script you
use; they are not shared.

| Constant | Default | Used by | Meaning |
|---|---|---|---|
| `GPIO_PIN` | `18` | all LED scripts | GPIO pin for the strip's data line |
| `NUM_LEDS` | `144` | all LED scripts | LEDs on the strip |
| `LED_BRIGHTNESS` | `255` | all LED scripts | Overall brightness, 0–255 |
| `BASE_NOTE` | `29` | all LED scripts | MIDI note lit by the first LED |
| `MIDI_PORT` | `20:0` | `piano-lights.py` | ALSA port passed to `aseqdump` |
| `MIDI_OUTPUT_PORT` | `CH345:CH345 MIDI 1 20:0` | `play-song.py`, `learn-song.py` | mido output port for your instrument |
| `MIDI_INPUT_PORT` | `CH345:CH345 MIDI 1 20:0` | `learn-song.py` | mido input port for your keyboard |

Each note lights LEDs `(note − BASE_NOTE) × 2` and the one after it. With the
defaults, the 144 LEDs cover 72 notes, from MIDI note 29 (F1) to note 100 (E7).
Notes outside that range are ignored.

## Architecture

Three independent scripts share one idea, a note-to-LED mapping, and each
carries its own copy of it:

```
USB MIDI keyboard ──► aseqdump ──► piano-lights.py ──┐
                                                    ├──► rpi-ws281x ──► GPIO 18 ──► WS2815 strip
MIDI file ──► mido ──► play-song.py / learn-song.py ─┘
                          │
                          └──► mido output ──► your instrument
                   (learn-song.py also reads the keyboard through mido)
```

| Path | Role |
|---|---|
| `piano-lights.py` | Live mode: parses `aseqdump` output line by line, with sustain-pedal handling |
| `play-song.py` | File playback with tempo, speed, repeat, fade and terminal-view options |
| `learn-song.py` | Plays a file and blocks on each note until the keyboard sends it |
| `list-midi-ports.py`, `dump-midi-in.sh` | Diagnostics for finding the right ports |
| `configure-python.sh`, `start-tmux.sh` | Setup and a background session |
| `midi/` | The bundled MIDI files |

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

Written by Geoff Myers.

## Contributing

Bug reports and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md)
for setup, checks and how this repository is published.

## License

GPL-2.0. See [LICENSE.md](LICENSE.md).
