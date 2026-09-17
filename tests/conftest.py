"""Shared test fixtures.

`rpi_ws281x` is a hardware extension for the WS281x LED driver; it only
builds against a Raspberry Pi's GPIO/DMA headers, so it is deliberately not a
test dependency (see requirements-dev.txt). Every test gets a fake module
installed in its place instead.

The project's scripts (`piano-lights.py`, `play-song.py`, `learn-song.py`)
are named for the command line (`python piano-lights.py`), not for
`import`, so a hyphen in the filename makes a plain `import piano_lights`
statement invalid. `load_script_module` loads them by file path instead.
"""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class FakeColor(int):
    """Packs (r, g, b) the same way rpi_ws281x.Color() does, so tests can
    compare the packed int against a plain (r, g, b) computation."""

    def __new__(cls, r, g, b):
        return int.__new__(cls, (r << 16) | (g << 8) | b)


class FakePixelStrip:
    """A minimal stand-in for rpi_ws281x.PixelStrip that records writes to
    an in-memory list instead of driving real GPIO/DMA hardware."""

    def __init__(self, num, pin, freq_hz, dma, invert, brightness, channel):
        self.num = num
        self._pixels = [0] * num
        self.show_calls = 0
        self.began = False

    def begin(self):
        self.began = True

    def setPixelColor(self, index, color):
        self._pixels[index] = int(color)

    def getPixelColor(self, index):
        return self._pixels[index]

    def show(self):
        self.show_calls += 1

    def numPixels(self):
        return self.num


@pytest.fixture(autouse=True)
def fake_rpi_ws281x(monkeypatch):
    fake_module = types.SimpleNamespace(PixelStrip=FakePixelStrip, Color=FakeColor)
    monkeypatch.setitem(sys.modules, "rpi_ws281x", fake_module)
    yield


@pytest.fixture
def load_script_module():
    def _load(name, filename):
        path = PROJECT_ROOT / filename
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    return _load
