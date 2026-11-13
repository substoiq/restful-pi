"""A thin layer over gpiozero that switches GPIO outputs on and off.

gpiozero is the GPIO library recommended by Raspberry Pi. It works on every
model, including the Raspberry Pi 5, where the old RPi.GPIO library does not.

To try everything without a Raspberry Pi, set GPIOZERO_PIN_FACTORY=mock:
gpiozero then simulates the pins in memory.
"""

import threading

from gpiozero import OutputDevice


class LedBoard:
    """Keeps one gpiozero OutputDevice per GPIO pin."""

    def __init__(self):
        self._devices = {}
        self._lock = threading.Lock()

    def add(self, pin_num: int, on: bool = False) -> None:
        with self._lock:
            if pin_num not in self._devices:
                self._devices[pin_num] = OutputDevice(pin_num, initial_value=on)
            else:
                self._devices[pin_num].value = on

    def set(self, pin_num: int, on: bool) -> None:
        with self._lock:
            self._devices[pin_num].value = on

    def is_on(self, pin_num: int) -> bool:
        with self._lock:
            return bool(self._devices[pin_num].value)

    def remove(self, pin_num: int) -> None:
        """Switch the pin off and release it, so it can be used again."""
        with self._lock:
            device = self._devices.pop(pin_num, None)
        if device is not None:
            device.off()
            device.close()

    def close(self) -> None:
        for pin_num in list(self._devices):
            self.remove(pin_num)
