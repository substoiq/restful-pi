"""RESTful Pi: a REST API that switches the GPIO pins of a Raspberry Pi.

Start it with:  python3 app.py
Then open:      http://<address-of-the-pi>:5000/docs
"""

import atexit
import os
import threading

from flask import Flask, redirect
from flask_restx import Api, Resource, fields

from leds import LedBoard
from pins import DEFAULT_PINS, MAX_PIN, MIN_PIN

STATES = ["on", "off"]


class PinStore:
    """The pins the API knows about, kept in memory.

    Every change is applied to the GPIO pin straight away. A lock makes sure
    that two requests at the same time cannot get in each other's way.
    """

    def __init__(self, board: LedBoard):
        self._board = board
        self._pins = {}
        self._next_id = 1
        self._lock = threading.Lock()

    def list(self):
        with self._lock:
            return [dict(pin) for pin in self._pins.values()]

    def get(self, pin_id: int):
        with self._lock:
            return dict(self._find(pin_id))

    def create(self, data: dict):
        with self._lock:
            self._check_free(data["pin_num"])
            pin = {
                "id": self._next_id,
                "pin_num": data["pin_num"],
                "color": data["color"],
                "state": data["state"],
            }
            self._board.add(pin["pin_num"], on=pin["state"] == "on")
            self._pins[pin["id"]] = pin
            self._next_id += 1
            return dict(pin)

    def update(self, pin_id: int, data: dict):
        """Change one or more fields. The id itself can never be changed."""
        with self._lock:
            pin = self._find(pin_id)
            changes = {key: data[key] for key in ("pin_num", "color", "state") if key in data}

            new_pin_num = changes.get("pin_num", pin["pin_num"])
            if new_pin_num != pin["pin_num"]:
                self._check_free(new_pin_num)
                # Move to another GPIO pin: switch the old one off and release it.
                self._board.remove(pin["pin_num"])
                self._board.add(new_pin_num)

            pin.update(changes)
            self._board.set(pin["pin_num"], pin["state"] == "on")
            return dict(pin)

    def delete(self, pin_id: int):
        with self._lock:
            pin = self._find(pin_id)
            self._board.remove(pin["pin_num"])
            del self._pins[pin_id]

    def _find(self, pin_id: int):
        pin = self._pins.get(pin_id)
        if pin is None:
            raise LookupError(f"pin {pin_id} doesn't exist")
        return pin

    def _check_free(self, pin_num: int):
        for pin in self._pins.values():
            if pin["pin_num"] == pin_num:
                raise ValueError(f"GPIO {pin_num} is already used by pin {pin['id']}")


def create_app(board: LedBoard = None, initial_pins=DEFAULT_PINS) -> Flask:
    board = board or LedBoard()
    store = PinStore(board)
    for pin in initial_pins:
        store.create({**pin, "state": "off"})

    app = Flask(__name__)
    app.config["RESTX_MASK_SWAGGER"] = False
    app.config["RESTX_ERROR_404_HELP"] = False
    app.extensions["pin_store"] = store

    @app.route("/")
    def index():
        return redirect("/docs")

    api = Api(
        app,
        version="2.0",
        title="RESTful Pi",
        description="A RESTful API to control the GPIO pins of a Raspberry Pi",
        doc="/docs",
    )
    ns = api.namespace("pins", description="Pin related operations")

    pin_num = {"min": MIN_PIN, "max": MAX_PIN, "example": 23,
               "description": "BCM GPIO number the LED is connected to"}
    color = {"min_length": 1, "example": "red", "description": "LED color"}
    state = {"enum": STATES, "example": "on", "description": "LED on or off"}

    pin_model = ns.model("Pin", {
        "id": fields.Integer(readonly=True, description="The pin unique identifier"),
        "pin_num": fields.Integer(**pin_num),
        "color": fields.String(**color),
        "state": fields.String(**state),
    })
    # PUT and POST need every field, PATCH accepts any subset.
    pin_input = ns.model("PinInput", {
        "pin_num": fields.Integer(required=True, **pin_num),
        "color": fields.String(required=True, **color),
        "state": fields.String(required=True, **state),
    })
    pin_patch = ns.model("PinPatch", {
        "pin_num": fields.Integer(**pin_num),
        "color": fields.String(**color),
        "state": fields.String(**state),
    })

    def run(action, *args):
        try:
            return action(*args)
        except LookupError as error:
            api.abort(404, str(error))
        except ValueError as error:
            api.abort(409, str(error))

    @ns.route("/")
    class PinList(Resource):
        """Shows a list of all pins, and lets you POST to add new pins"""

        @ns.marshal_list_with(pin_model)
        def get(self):
            """List all pins"""
            return store.list()

        @ns.expect(pin_input, validate=True)
        @ns.response(409, "GPIO pin already in use")
        @ns.marshal_with(pin_model, code=201)
        def post(self):
            """Create a new pin"""
            return run(store.create, api.payload), 201

    @ns.route("/<int:id>")
    @ns.response(404, "Pin not found")
    @ns.param("id", "The pin identifier")
    class Pin(Resource):
        """Show a single pin and lets you update or delete it"""

        @ns.marshal_with(pin_model)
        def get(self, id):
            """Fetch a pin given its identifier"""
            return run(store.get, id)

        @ns.expect(pin_input, validate=True)
        @ns.response(409, "GPIO pin already in use")
        @ns.marshal_with(pin_model)
        def put(self, id):
            """Replace all fields of a pin"""
            return run(store.update, id, api.payload)

        @ns.expect(pin_patch, validate=True)
        @ns.response(409, "GPIO pin already in use")
        @ns.marshal_with(pin_model)
        def patch(self, id):
            """Change one or more fields of a pin, for example only the state"""
            return run(store.update, id, api.payload)

        @ns.response(204, "Pin deleted")
        def delete(self, id):
            """Delete a pin and switch its LED off"""
            run(store.delete, id)
            return "", 204

    return app


if __name__ == "__main__":
    board = LedBoard()
    atexit.register(board.close)  # all LEDs off when the app stops

    host = os.environ.get("RESTFUL_PI_HOST", "127.0.0.1")
    port = int(os.environ.get("RESTFUL_PI_PORT", "5000"))
    create_app(board).run(host=host, port=port)
