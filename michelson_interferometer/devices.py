#!/usr/bin/env python3
# Michelson Interferometer Control Software
# https://github.com/gucci-on-fleek/michelson-interferometer
# SPDX-License-Identifier: MPL-2.0+
# SPDX-FileCopyrightText: 2025 Max Chernoff

###############
### Imports ###
###############

from glob import glob
from threading import Lock
from time import sleep
from time import time as unix_time
from typing import Any, Callable

from pylablib.core.devio.SCPI import SCPIDevice
from pylablib.devices.Thorlabs import KinesisMotor

from .utils import start_thread

#################
### Constants ###
#################

MOTOR_DEVICE_GLOB = "/dev/ttyUSB?"
DETECTOR_DEVICE_GLOB = "/dev/ttyACM?"

# For a KBD101/DDSM50 controller, from Thorlabs documentation:
#     https://www.thorlabs.com/Software/Motion%20Control/APT_Communications_Protocol.pdf
MOTOR_SCALE = (2_000, 13_421.77, 1.374)
MOTOR_MAX_POS = 50.0  # millimeters

DETECTOR_BAUD = 115_200
DETECTOR_TIMEOUT = 0.05  # seconds
DETECTOR_NL = "\n"

SLEEP_DURATION = 1 / 10  # seconds


#########################
### Class Definitions ###
#########################


class Motor:
    """Controls the motor that moves the mirror."""

    def __init__(self, on_update: Callable[[float], Any]) -> None:
        try:
            path = glob(MOTOR_DEVICE_GLOB)[0]
        except IndexError:
            raise IOError("No motor device found")

        self._device = KinesisMotor(
            path,
            scale=MOTOR_SCALE,  # type: ignore[arg-type]
        )

        self.on_update = on_update
        self.data: list[tuple[float, float]] = []
        self._thread = start_thread(self._run_thread)
        self._lock = Lock()

        self.home()

    def home(self) -> None:
        """Homes the motor."""
        with self._lock:
            self._device.home(force=True, sync=False)

    def stop(self) -> None:
        """Stops the motor."""
        with self._lock:
            self._device.stop()

    def wait(self) -> None:
        """Waits for the motor to finish any current movement."""
        with self._lock:
            self._device.wait_for_stop()

    @property
    def position(self) -> float:
        """Gets the current position of the mirror in millimeters."""
        with self._lock:
            return self._device.get_position()

    @position.setter
    def position(self, value: float) -> None:
        """Sets the position of the mirror in millimeters."""
        with self._lock:
            self._device.move_to(value)
            sleep(SLEEP_DURATION / 2)

    def _run_thread(self) -> None:
        """Calls the on_update callback with the current position."""
        while True:
            sleep(SLEEP_DURATION)
            self.data.append((unix_time(), self.position))
            self.on_update(self.position)


class Detector:
    """Controls the light intensity detector."""

    def __init__(self, on_update: Callable[[int], Any]) -> None:
        try:
            path = glob(DETECTOR_DEVICE_GLOB)[0]
        except IndexError:
            raise IOError("No detector device found")

        self._device = SCPIDevice(
            (path, DETECTOR_BAUD),
            timeout=DETECTOR_TIMEOUT,
            term_write=DETECTOR_NL,
        )

        self.on_update = on_update
        self.data: list[tuple[float, int]] = []
        self._thread = start_thread(self._run_thread)

        assert self._device.get_id()

    @property
    def gain(self) -> int:
        """Gets the current position of the mirror in millimeters."""
        value = self._device.ask("det:gain?", "int")
        assert isinstance(value, int)
        return value

    @gain.setter
    def gain(self, value: int) -> None:
        """Sets the position of the mirror in millimeters."""
        self._device.write(f"det:gain {value}")
        sleep(0.1)  # Give the detector time to adjust, hack!

    @property
    def intensity(self) -> int:
        """Gets the current light intensity reading from the detector."""
        value = self._device.ask("det:meas?", "int")
        assert isinstance(value, int)
        return value

    def _run_thread(self) -> None:
        """Calls the on_update callback with the current intensity."""
        while True:
            sleep(SLEEP_DURATION)
            self.data.append((unix_time(), self.intensity))
            self.on_update(self.intensity)
