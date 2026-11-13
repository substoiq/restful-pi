"""Run every test against simulated GPIO pins, so no Raspberry Pi is needed."""

import os
import sys

os.environ["GPIOZERO_PIN_FACTORY"] = "mock"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from gpiozero import Device


@pytest.fixture(autouse=True)
def reset_pins():
    yield
    Device.pin_factory.reset()


def gpio_is_on(pin_num: int) -> bool:
    return bool(Device.pin_factory.pin(pin_num).state)
