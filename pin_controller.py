"""Control the LEDs directly through the GPIO pins, without the API.

From the command line:

    python3 pin_controller.py wave --period 0.1
    python3 pin_controller.py rainbow --run-time 20

Or from a Python shell:

    >>> import pin_controller
    >>> pin_controller.color_on("red")
    >>> pin_controller.wave(period=0.05, run_time=10)

Don't run this while app.py is running: both want the same GPIO pins.
"""

import atexit
import functools

import patterns
from leds import LedBoard
from pins import DEFAULT_PINS


class GpioLeds:
    """The "leds" object for patterns.py, talking to the GPIO pins directly."""

    def __init__(self, board: LedBoard, pins=DEFAULT_PINS):
        self._board = board
        self._pins = [dict(pin) for pin in pins]
        for pin in self._pins:
            board.add(pin["pin_num"])

    def pins(self):
        return [{**pin, "state": "on" if self._board.is_on(pin["pin_num"]) else "off"}
                for pin in self._pins]

    def set(self, pin, state: str):
        self._board.set(pin["pin_num"], state == "on")


_instance = None


def _leds() -> GpioLeds:
    """Claim the GPIO pins on first use, and release them when Python exits."""
    global _instance
    if _instance is None:
        board = LedBoard()
        atexit.register(board.close)
        _instance = GpioLeds(board)
    return _instance


def _bind(function):
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        return function(_leds(), *args, **kwargs)
    return wrapper


def pin_on(pin_num: int):
    _leds().set({"pin_num": pin_num}, "on")


def pin_off(pin_num: int):
    _leds().set({"pin_num": pin_num}, "off")


switch_all = _bind(patterns.switch_all)
all_on = _bind(patterns.all_on)
all_off = _bind(patterns.all_off)
toggle_color = _bind(patterns.toggle_color)
color_on = _bind(patterns.color_on)
color_off = _bind(patterns.color_off)

on_off = _bind(patterns.on_off)
strobe_rand = _bind(patterns.strobe_rand)
wave = _bind(patterns.wave)
wave_rand = _bind(patterns.wave_rand)
wave_rand_ex = _bind(patterns.wave_rand_ex)
rainbow = _bind(patterns.rainbow)
single_rand = _bind(patterns.single_rand)
random_stuff = _bind(patterns.random_stuff)

# The names used in earlier versions
strobe_reg = on_off
wave_reg = wave


if __name__ == "__main__":
    parser = patterns.make_parser("Run a light pattern directly on the GPIO pins.")
    patterns.run_from_args(_leds(), parser.parse_args())
