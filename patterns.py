"""Light patterns, shared by pin_controller.py (direct GPIO) and lightshow.py (via the API).

Every pattern takes a "leds" object with two methods:

    leds.pins()           -> list of pins; each is a dict with at least "color" and "state"
    leds.set(pin, state)  -> switch one pin "on" or "off"

Patterns run until run_time seconds have passed, or forever when run_time is None.
Stop a pattern that runs forever with Ctrl+C.
"""

import argparse
import inspect
import random
import time

COLORS = ["red", "blue", "green", "yellow"]


def _running(run_time):
    """Yield once per round until run_time seconds have passed (or forever)."""
    end = None if run_time is None else time.monotonic() + run_time
    while end is None or time.monotonic() < end:
        yield


# ---------- Simple switches ----------

def switch_all(leds, state: str):
    for pin in leds.pins():
        if pin["state"] != state:  # don't bother switching pins that are already right
            leds.set(pin, state)


def all_on(leds):
    switch_all(leds, "on")


def all_off(leds):
    switch_all(leds, "off")


def toggle_color(leds, color: str, state: str):
    for pin in leds.pins():
        if pin["color"] == color and pin["state"] != state:
            leds.set(pin, state)


def color_on(leds, color: str):
    toggle_color(leds, color, "on")


def color_off(leds, color: str):
    toggle_color(leds, color, "off")


# ---------- Patterns ----------

def on_off(leds, period=0.5, run_time=None):
    """All LEDs on and off at a steady pace."""
    for _ in _running(run_time):
        all_on(leds)
        time.sleep(period)
        all_off(leds)
        time.sleep(period)


def strobe_rand(leds, min_time=0.0, max_time=1.2, run_time=None):
    """All LEDs on and off at a random pace."""
    for _ in _running(run_time):
        all_on(leds)
        time.sleep(random.uniform(min_time, max_time))
        all_off(leds)
        time.sleep(random.uniform(min_time, max_time))


def wave(leds, period=0.1, run_time=None):
    """Switch the LEDs on one by one, then off again in reverse order."""
    for _ in _running(run_time):
        pins = leds.pins()
        for pin in pins:
            leds.set(pin, "on")
            time.sleep(period)
        for pin in reversed(pins):
            leds.set(pin, "off")
            time.sleep(period)


def wave_rand(leds, min_time=0.0, max_time=0.4, run_time=None):
    """A wave with a random speed for each direction."""
    for _ in _running(run_time):
        pins = leds.pins()
        period = random.uniform(min_time, max_time)
        for pin in pins:
            leds.set(pin, "on")
            time.sleep(period)
        period = random.uniform(min_time, max_time)
        for pin in reversed(pins):
            leds.set(pin, "off")
            time.sleep(period)


def wave_rand_ex(leds, min_time=0.0, max_time=0.4, run_time=None):
    """A wave with a random pause after every single LED."""
    for _ in _running(run_time):
        pins = leds.pins()
        for pin in pins:
            leds.set(pin, "on")
            time.sleep(random.uniform(min_time, max_time))
        for pin in reversed(pins):
            leds.set(pin, "off")
            time.sleep(random.uniform(min_time, max_time))


def rainbow(leds, period=0.5, run_time=None):
    """One color at a time."""
    for _ in _running(run_time):
        for color in COLORS:
            color_on(leds, color)
            time.sleep(period)
            color_off(leds, color)


def single_rand(leds, period=0.1, run_time=None):
    """One random LED at a time."""
    for _ in _running(run_time):
        pin = random.choice(leds.pins())
        leds.set(pin, "on")
        time.sleep(period)
        leds.set(pin, "off")


def random_stuff(leds, max_period=0.5, run_time=None):
    """A random mix of everything above."""
    for _ in _running(run_time):
        random.choice([all_on, all_off])(leds)
        time.sleep(random.uniform(0.1, max_period))
        for _step in range(2):
            random.choice([color_on, color_off])(leds, random.choice(COLORS))
            time.sleep(random.uniform(0.1, max_period))


PATTERNS = {
    "on_off": on_off,
    "strobe_rand": strobe_rand,
    "wave": wave,
    "wave_rand": wave_rand,
    "wave_rand_ex": wave_rand_ex,
    "rainbow": rainbow,
    "single_rand": single_rand,
    "random_stuff": random_stuff,
}


# ---------- Command line ----------

def make_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("pattern", choices=sorted(PATTERNS), help="the pattern to run")
    parser.add_argument("--run-time", type=float, help="stop after this many seconds (default: run until Ctrl+C)")
    parser.add_argument("--period", type=float, help="seconds per step, for patterns with a steady pace")
    parser.add_argument("--min-time", type=float, help="shortest random pause in seconds")
    parser.add_argument("--max-time", type=float, help="longest random pause in seconds")
    parser.add_argument("--max-period", type=float, help="longest pause for random_stuff")
    return parser


def run_from_args(leds, args) -> None:
    """Run the chosen pattern with the options it understands, and switch everything off at the end."""
    pattern = PATTERNS[args.pattern]
    accepted = inspect.signature(pattern).parameters
    options = {
        name: getattr(args, name)
        for name in ("run_time", "period", "min_time", "max_time", "max_period")
        if name in accepted and getattr(args, name) is not None
    }
    try:
        pattern(leds, **options)
    except KeyboardInterrupt:
        pass
    finally:
        all_off(leds)
