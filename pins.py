"""The LED layout on the breadboard, shared by the API and the scripts.

Pin numbers are BCM GPIO numbers (the "GPIO23" names), not the physical
pin positions on the header. Change this list to match your own wiring.
"""

DEFAULT_PINS = [
    {"pin_num": 23, "color": "red"},
    {"pin_num": 24, "color": "yellow"},
    {"pin_num": 25, "color": "blue"},
    {"pin_num": 22, "color": "red"},
    {"pin_num": 12, "color": "yellow"},
    {"pin_num": 16, "color": "blue"},
    {"pin_num": 20, "color": "red"},
    {"pin_num": 21, "color": "green"},
    {"pin_num": 13, "color": "yellow"},
]

COLORS = sorted({pin["color"] for pin in DEFAULT_PINS})

# GPIO 0 and 1 are reserved for the HAT ID EEPROM; 2 to 27 are on the 40-pin header.
MIN_PIN = 2
MAX_PIN = 27
