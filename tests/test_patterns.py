"""Run the patterns against the GPIO pins and against the live API."""

import threading

import pytest
from werkzeug.serving import make_server

import patterns
from app import create_app
from conftest import gpio_is_on
from leds import LedBoard
from lightshow import ApiLeds
from pin_controller import GpioLeds
from pins import DEFAULT_PINS


class RecordingLeds:
    """Wraps a leds object and remembers every switch, to check what a pattern did."""

    def __init__(self, inner):
        self.inner = inner
        self.calls = []

    def pins(self):
        return self.inner.pins()

    def set(self, pin, state):
        self.calls.append((pin["pin_num"], state))
        self.inner.set(pin, state)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(patterns.time, "sleep", lambda seconds: None)


@pytest.fixture
def gpio_leds():
    board = LedBoard()
    yield GpioLeds(board)
    board.close()


@pytest.fixture
def api_url():
    server = make_server("127.0.0.1", 0, create_app())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_color_on_switches_only_that_color(gpio_leds):
    patterns.color_on(gpio_leds, "red")
    for pin in DEFAULT_PINS:
        assert gpio_is_on(pin["pin_num"]) == (pin["color"] == "red")


def test_switch_all_skips_pins_that_are_already_right(gpio_leds):
    leds = RecordingLeds(gpio_leds)
    patterns.color_on(leds, "red")
    leds.calls.clear()
    patterns.all_on(leds)
    assert len(leds.calls) == len(DEFAULT_PINS) - 3  # the three red ones were already on


def test_wave_goes_up_and_back_down(gpio_leds):
    leds = RecordingLeds(gpio_leds)
    patterns.wave(leds, run_time=0.000001)
    pin_nums = [pin["pin_num"] for pin in DEFAULT_PINS]
    assert leds.calls == [(n, "on") for n in pin_nums] + [(n, "off") for n in reversed(pin_nums)]


@pytest.mark.parametrize("name", sorted(patterns.PATTERNS))
def test_every_pattern_runs_and_stops(gpio_leds, name):
    patterns.PATTERNS[name](gpio_leds, run_time=0.01)


@pytest.mark.parametrize("method", ["patch", "put"])
def test_lightshow_through_the_api(api_url, method):
    leds = ApiLeds(api_url, method)
    patterns.color_on(leds, "green")
    states = {pin["color"]: pin["state"] for pin in leds.pins() if pin["color"] == "green"}
    assert states == {"green": "on"}
    assert gpio_is_on(21)

    patterns.wave_rand_ex(leds, run_time=0.01)  # this pattern crashed in the old lightshow.py
    patterns.all_off(leds)
    assert all(pin["state"] == "off" for pin in leds.pins())


def test_run_from_args_switches_everything_off_at_the_end(gpio_leds):
    args = patterns.make_parser("test").parse_args(["on_off", "--run-time", "0.01", "--period", "0"])
    patterns.run_from_args(gpio_leds, args)
    assert not any(gpio_is_on(pin["pin_num"]) for pin in DEFAULT_PINS)
