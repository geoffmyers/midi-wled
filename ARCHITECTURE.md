---
title: Architecture
description: How MIDI input is mapped to addressable LED output on a Raspberry Pi.
---

# Architecture

A set of small Python scripts that read MIDI and drive a WS281x LED strip,
intended to sit behind or above a piano keyboard.

## Layout

| Path | What lives there |
|---|---|
| `piano-lights.py` | The main loop — open a MIDI port, map notes to LEDs, render. |
| `learn-song.py`, `play-song.py` | Record and replay note sequences for practice. |
| `list-midi-ports.py`, `dump-midi-in.sh` | Diagnostics for finding and inspecting an input device. |
| `midi/` | Song data. |
| `configure-python.sh`, `start-tmux.sh` | Host setup and a long-running session wrapper. |

## Notes

- MIDI I/O uses `mido` over `python-rtmidi`; LED output uses `rpi-ws281x`, which
  needs root (or the appropriate capability) for PWM/DMA access.
- Note-to-LED mapping depends on the physical strip density and where it sits
  relative to the keys; that offset is the first thing to adjust.
- `old/` and `chatgpt/` hold earlier experiments and are not part of the running
  program.
