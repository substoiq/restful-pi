# RESTful Pi

A small REST API that switches the GPIO pins of a Raspberry Pi. Every LED on a breadboard becomes a resource at `/pins/<id>`; a `PATCH` with `{"state": "on"}` lights it up. Two scripts turn that into a light show: one through the API, from any computer on your network, and one directly on the GPIO pins.

Built with Python 3, [Flask](https://flask.palletsprojects.com/), [Flask-RESTX](https://flask-restx.readthedocs.io/) and [gpiozero](https://gpiozero.readthedocs.io/). Works on every Raspberry Pi model, including the Raspberry Pi 5.

> This is a modernised fork of [avcourt/restful-pi](https://github.com/avcourt/restful-pi) by avcourt, who also wrote a [step-by-step tutorial](https://avcourt.github.io/tiny-cluster/2019/09/18/pi_led.html) and a [video series](https://www.youtube.com/playlist?list=PLLIDdNg0t5ceg3mI3vn0YJocJ4ndMtM98) about the original version. See [What changed](#what-changed) for the differences.

## What you need

- A Raspberry Pi with Raspberry Pi OS (Bookworm or newer)
- 9 LEDs, preferably in several colors (3 red, 3 yellow, 2 blue and 1 green in this setup)
- 9 resistors of 220 Ω to 1 kΩ, one per LED
- A breadboard and 10 jumper wires

### Wiring

Each LED goes from a GPIO pin, through a resistor, to ground. The code uses these pins:

| GPIO | Color | | GPIO | Color | | GPIO | Color |
|---:|---|---|---:|---|---|---:|---|
| 23 | red | | 22 | red | | 20 | red |
| 24 | yellow | | 12 | yellow | | 21 | green |
| 25 | blue | | 16 | blue | | 13 | yellow |

These are **BCM GPIO numbers** (the "GPIO23" names), not the physical pin positions on the header. Using other pins or colors? Change the list in [`pins.py`](pins.py); the API and both scripts read it from there.

![GPIO numbering](img/rpi_gpio.jpg)

![Schematic](img/schematic.png)

## Installation

Raspberry Pi OS no longer lets `pip` install packages system-wide, so the app gets its own virtual environment. The `--system-site-packages` option lets it use the GPIO libraries that come with Raspberry Pi OS.

```bash
git clone https://github.com/substoiq/restful-pi.git
cd restful-pi
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the API

```bash
python3 app.py
```

Then open <http://localhost:5000/docs> on the Pi for the interactive Swagger UI, where you can try every request.

By default the API only listens on the Pi itself. To reach it from other computers on your network:

```bash
RESTFUL_PI_HOST=0.0.0.0 python3 app.py
```

and open `http://<address-of-your-pi>:5000/docs`.

> The API has no authentication. Anyone who can reach port 5000 can switch your pins. Only open it up on a network you trust.

| Environment variable | Default | Meaning |
|---|---|---|
| `RESTFUL_PI_HOST` | `127.0.0.1` | Address the API listens on |
| `RESTFUL_PI_PORT` | `5000` | Port the API listens on |

All LEDs are switched off when the app stops.

### Try it without a Raspberry Pi

gpiozero can simulate the pins in memory. That lets you run the API, the scripts and the tests on any computer:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
GPIOZERO_PIN_FACTORY=mock python3 app.py
```

## The API

A pin looks like this:

```json
{
  "id": 1,
  "pin_num": 23,
  "color": "red",
  "state": "off"
}
```

| Field | Type | Rules |
|---|---|---|
| `id` | integer | Assigned by the API, read-only |
| `pin_num` | integer | BCM GPIO number, 2 to 27, each pin only once |
| `color` | string | Any non-empty text |
| `state` | string | `"on"` or `"off"` |

| Request | Does | Success |
|---|---|---|
| `GET /pins/` | List all pins | 200 |
| `POST /pins/` | Add a pin; needs `pin_num`, `color` and `state` | 201 |
| `GET /pins/<id>` | Fetch one pin | 200 |
| `PUT /pins/<id>` | Replace a pin; needs `pin_num`, `color` and `state` | 200 |
| `PATCH /pins/<id>` | Change one or more fields, for example only `state` | 200 |
| `DELETE /pins/<id>` | Remove a pin and switch its LED off | 204 |

Errors:

| Status | When |
|---|---|
| 400 | Missing field, wrong type, `state` other than `on`/`off`, or `pin_num` outside 2–27 |
| 404 | No pin with that id |
| 409 | The GPIO pin is already used by another pin |

### Examples with curl

```bash
# All pins
curl http://localhost:5000/pins/

# Switch pin 1 on
curl -X PATCH http://localhost:5000/pins/1 \
     -H "Content-Type: application/json" -d '{"state": "on"}'

# Replace pin 2 completely
curl -X PUT http://localhost:5000/pins/2 \
     -H "Content-Type: application/json" \
     -d '{"pin_num": 24, "color": "yellow", "state": "on"}'

# Add an LED on GPIO 5
curl -X POST http://localhost:5000/pins/ \
     -H "Content-Type: application/json" \
     -d '{"pin_num": 5, "color": "white", "state": "off"}'

# Remove it again
curl -X DELETE http://localhost:5000/pins/10
```

## Light shows

There are two ways to run the same light patterns:

| Script | Talks to | Use it |
|---|---|---|
| `lightshow.py` | The REST API | From any computer that can reach the Pi, while `app.py` runs |
| `pin_controller.py` | The GPIO pins directly | On the Pi itself, while `app.py` is **not** running |

Both take a pattern name and options:

```bash
python3 lightshow.py rainbow
python3 lightshow.py wave --period 0.05 --url http://raspberrypi.local:5000
python3 lightshow.py on_off --method put --run-time 30

python3 pin_controller.py wave_rand --min-time 0 --max-time 0.2
```

| Pattern | What it does | Options |
|---|---|---|
| `on_off` | All LEDs on and off at a steady pace | `--period` |
| `strobe_rand` | All LEDs on and off at a random pace | `--min-time`, `--max-time` |
| `wave` | LEDs on one by one, then off in reverse | `--period` |
| `wave_rand` | A wave with a random speed per direction | `--min-time`, `--max-time` |
| `wave_rand_ex` | A wave with a random pause after every LED | `--min-time`, `--max-time` |
| `rainbow` | One color at a time | `--period` |
| `single_rand` | One random LED at a time | `--period` |
| `random_stuff` | A random mix of everything | `--max-period` |

Every pattern accepts `--run-time` to stop after a number of seconds; without it, it runs until you press Ctrl+C. Either way, all LEDs are switched off at the end.

`lightshow.py` also takes:

- `--url`: the address of the API. You can also set it once with the `RESTFUL_PI_URL` environment variable. Default: `http://localhost:5000`.
- `--method`: `patch` (default) sends only `{"state": ...}`; `put` sends the whole pin. Handy to see the difference between the two HTTP methods.

### From a Python shell

```python
>>> import lightshow
>>> lightshow.color_on("red")
>>> lightshow.all_off()
>>> lightshow.wave(period=0.05, run_time=10)
```

`pin_controller` has the same functions, plus `pin_on(pin_num)` and `pin_off(pin_num)`.

### Writing your own pattern

Patterns live in [`patterns.py`](patterns.py). A pattern is a function that gets a `leds` object with two methods, `leds.pins()` and `leds.set(pin, state)`, so it works through the API and directly on the GPIO pins without changes:

```python
def blink_green(leds, period=0.3, run_time=None):
    for _ in _running(run_time):
        color_on(leds, "green")
        time.sleep(period)
        color_off(leds, "green")
        time.sleep(period)
```

Add it to the `PATTERNS` dictionary at the bottom of the file and both scripts can run it.

## Running the API as a service

To start the API automatically when the Pi boots, create `/etc/systemd/system/restful-pi.service` (replace `<user>` with your user name):

```ini
[Unit]
Description=RESTful Pi
After=network-online.target
Wants=network-online.target

[Service]
User=<user>
WorkingDirectory=/home/<user>/restful-pi
Environment=RESTFUL_PI_HOST=0.0.0.0
ExecStart=/home/<user>/restful-pi/.venv/bin/python app.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now restful-pi
```

## Project layout

| File | Contents |
|---|---|
| `app.py` | The REST API |
| `pins.py` | The LED layout: GPIO number and color per LED |
| `leds.py` | Switches GPIO pins through gpiozero |
| `patterns.py` | The light patterns and the shared command-line options |
| `lightshow.py` | Runs patterns through the API |
| `pin_controller.py` | Runs patterns directly on the GPIO pins |
| `tests/` | Tests, run against simulated pins |

## Tests

The tests use gpiozero's simulated pins, so they run on any computer:

```bash
pip install -r requirements-dev.txt
python3 -m pytest
```

## What changed

Compared with the original project:

**It runs again on current hardware and software**

- Flask-RESTPlus is no longer maintained and fails to import on Python 3.10 and newer. It is replaced by its maintained successor, Flask-RESTX, which keeps the same API and Swagger UI.
- RPi.GPIO does not work on the Raspberry Pi 5. It is replaced by gpiozero, the library Raspberry Pi recommends, which works on every model.
- Dependencies are no longer pinned to 2019 versions with known security issues.
- The installation uses a virtual environment, because Raspberry Pi OS Bookworm no longer allows `pip install` system-wide.

**Bugs fixed**

- `toggle_color` in `lightshow.py` built its URL from the whole pin instead of its id, so `color_on` and `color_off` never reached the right pin. (The same bug was in `collab.py`.)
- `wave_rand_ex` in `lightshow.py` crashed on an undefined variable.
- A request could overwrite a pin's `id` by including it in the body.
- `state` accepted any text; anything other than `on` or `off` was stored without switching the LED.
- Moving a pin to another GPIO number left the old pin switched on.
- Two pins could use the same GPIO number.
- The API ran in Flask's debug mode, which is meant for development only. It also started the app twice, so the GPIO pins were set up twice.

**Simpler to work with**

- One pin list in `pins.py` instead of a copy in three files.
- The light patterns are written once in `patterns.py` and shared by both scripts. `auto_timed.py`, `lightshow_put.py` and `collab.py` are merged in: every pattern now has `run_time`, and `lightshow.py` has `--method put` and `--url`.
- Both scripts have a command line, and switch all LEDs off when you stop them.
- `lightshow.py` reuses one HTTP connection instead of opening a new one per request, and has a timeout.
- Tests that run without a Raspberry Pi.
