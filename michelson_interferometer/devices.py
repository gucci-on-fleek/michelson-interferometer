#!/usr/bin/env python3
# Michelson Interferometer Control Software
# https://github.com/gucci-on-fleek/michelson-interferometer
# SPDX-License-Identifier: MPL-2.0+
# SPDX-FileCopyrightText: 2025 Max Chernoff

###############
### Imports ###
###############

from glob import glob
from typing import Callable
from threading import Thread
from time import sleep

from pylablib.core.devio.SCPI import SCPIDevice
from pylablib.devices.Thorlabs import KinesisMotor

#################
### Constants ###
#################

MOTOR_DEVICE_GLOB = "/host-dev/ttyUSB?"
DETECTOR_DEVICE_GLOB = "/host-dev/ttyACM?"

# For a KBD101/DDSM50 controller, from Thorlabs documentation:
#     https://www.thorlabs.com/Software/Motion%20Control/APT_Communications_Protocol.pdf
MOTOR_SCALE = (2_000, 13_421.77, 1.374)
MOTOR_MAX_POS = 50.0  # millimeters

DETECTOR_BAUD = 115_200
DETECTOR_TIMEOUT = 0.1  # seconds
DETECTOR_NL = "\n"

SLEEP_DURATION = 1 / 30  # seconds


############################
### Function Definitions ###
############################


def threaded(func: Callable) -> Callable:
    """Decorator to run a function in a separate thread."""

    def wrapper(*args, **kwargs):
        thread = Thread(target=func, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread

    return wrapper


#########################
### Class Definitions ###
#########################


class Motor:
    """Controls the motor that moves the mirror."""

    def __init__(self, on_update=None) -> None:
        try:
            path = glob(MOTOR_DEVICE_GLOB)[0]
        except IndexError:
            raise IOError("No motor device found")

        self._device = KinesisMotor(
            path,
            scale=MOTOR_SCALE,  # type: ignore[arg-type]
        )

        self.on_update: Callable[[float], None] | None = on_update

        self.home()

    def home(self) -> None:
        """Homes the motor."""
        self._device.home(force=True)

    @property
    def position(self) -> float:
        """Gets the current position of the mirror in millimeters."""
        return self._device.get_position()

    @position.setter
    def position(self, value: float) -> None:
        """Sets the position of the mirror in millimeters."""
        self._device.move_to(value)
        self.update_position()

    @threaded
    def update_position(self) -> None:
        """Calls the on_update callback with the current position."""
        while self._device.is_moving():
            sleep(SLEEP_DURATION)
            if self.on_update:
                self.on_update(self.position)


class Detector:
    """Controls the light intensity detector."""

    def __init__(self, on_update=None) -> None:
        try:
            path = glob(DETECTOR_DEVICE_GLOB)[0]
        except IndexError:
            raise IOError("No detector device found")

        self._device = SCPIDevice(
            (path, DETECTOR_BAUD),
            timeout=DETECTOR_TIMEOUT,
            term_write=DETECTOR_NL,
        )

        self.on_update: Callable[[int], None] | None = on_update

        assert self._device.get_id()

    @property
    def intensity(self) -> int:
        """Gets the current light intensity reading from the detector."""
        value = self._device.ask("det:meas?", "int")
        assert isinstance(value, int)
        return value

    @threaded
    def update_value(self) -> None:
        """Calls the on_update callback with the current intensity."""
        while True:
            sleep(SLEEP_DURATION)
            if self.on_update:
                self.on_update(self.intensity)
