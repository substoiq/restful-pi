"""Run a light show through the REST API, from any computer that can reach the Pi.

From the command line:

    python3 lightshow.py rainbow
    python3 lightshow.py wave --period 0.05 --url http://raspberrypi.local:5000
    python3 lightshow.py on_off --method put --run-time 30

Or from a Python shell:

    >>> import lightshow
    >>> lightshow.color_on("red")
    >>> lightshow.wave(period=0.05, run_time=10)

The address of the API comes from --url, or from the environment variable
RESTFUL_PI_URL, and is http://localhost:5000 by default.
"""

import functools
import os

import requests

import patterns

DEFAULT_URL = os.environ.get("RESTFUL_PI_URL", "http://localhost:5000")
TIMEOUT = 5  # seconds


class ApiLeds:
    """The "leds" object for patterns.py, talking to the REST API.

    method="patch" sends only the new state; method="put" sends the whole pin,
    to show the difference between the two HTTP methods.
    """

    def __init__(self, url: str = DEFAULT_URL, method: str = "patch"):
        if method not in ("patch", "put"):
            raise ValueError("method must be 'patch' or 'put'")
        self._pins_url = url.rstrip("/") + "/pins/"
        self._method = method
        # One session reuses the same connection for every request, which is a lot faster.
        self._session = requests.Session()

    def pins(self):
        response = self._session.get(self._pins_url, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()

    def set(self, pin, state: str):
        url = f"{self._pins_url}{pin['id']}"
        if self._method == "patch":
            response = self._session.patch(url, json={"state": state}, timeout=TIMEOUT)
        else:
            body = {"pin_num": pin["pin_num"], "color": pin["color"], "state": state}
            response = self._session.put(url, json=body, timeout=TIMEOUT)
        response.raise_for_status()


_instance = None


def _leds() -> ApiLeds:
    global _instance
    if _instance is None:
        _instance = ApiLeds()
    return _instance


def _bind(function):
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        return function(_leds(), *args, **kwargs)
    return wrapper


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


if __name__ == "__main__":
    parser = patterns.make_parser("Run a light pattern through the RESTful Pi API.")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"address of the API (default: {DEFAULT_URL})")
    parser.add_argument("--method", choices=["patch", "put"], default="patch",
                        help="HTTP method for switching a pin (default: patch)")
    args = parser.parse_args()
    patterns.run_from_args(ApiLeds(args.url, args.method), args)
