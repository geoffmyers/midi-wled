# Architecture

A set of small Python scripts that read MIDI and drive a WS281x LED strip,
intended to sit behind or above a piano keyboard.

## Layout

| Path | What lives there |
|---|---|
| `led_piano.py` | Shared module: LED/GPIO constants, the note-to-LED mapping, octave colour and velocity-brightness math, and `LedStrip`, a thread-safe wrapper around `rpi_ws281x`. All three scripts below import this instead of keeping their own copy. |
| `piano-lights.py` | The main loop — open a MIDI port, map notes to LEDs, render. |
| `play-song.py`, `learn-song.py` | Play a MIDI file through your instrument with the strip in sync; `learn-song.py` waits for you to play each note. |
| `list-midi-ports.py`, `dump-midi-in.sh` | Diagnostics for finding and inspecting an input device. |
| `midi/` | Your song files, if you keep them here. None are published: see *Getting MIDI files* in the README. |
| `configure-python.sh`, `start-tmux.sh` | Host setup and a long-running session wrapper. |
| `tests/` | Pytest unit tests for `led_piano.py` and the three scripts' pure logic (mapping, colour, brightness, `adjust_tempo()`, note-off dispatch), run without hardware. `rpi_ws281x` is faked; see `tests/conftest.py`. |

## Notes

- MIDI I/O uses `mido` over `python-rtmidi`; LED output uses `rpi-ws281x`, which
  needs root (or the appropriate capability) for PWM/DMA access.
- Note-to-LED mapping depends on the physical strip density and where it sits
  relative to the keys; that offset is the first thing to adjust (`BASE_NOTE`
  in `led_piano.py`).
- The note-to-LED mapping and the LED/GPIO constants live in one place,
  `led_piano.py`; `piano-lights.py`, `play-song.py` and `learn-song.py` all
  import it, so a change (LED count, strip offset, colour scheme) only needs
  to be made once. Each script still keeps its own MIDI port name(s), since
  those are specific to its role (live input, file output, or both).
- `LedStrip` (in `led_piano.py`) serialises every write behind one lock. That
  matters because `play-song.py --fade` spawns a short-lived thread per note
  release; without the shared lock, an overlapping fade and a new note-on
  could both call `strip.show()` at once and interleave a half-written frame.
