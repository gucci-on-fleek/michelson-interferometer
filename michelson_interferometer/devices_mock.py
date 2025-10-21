#!/usr/bin/env python3
# Michelson Interferometer Control Software
# https://github.com/gucci-on-fleek/michelson-interferometer
# SPDX-License-Identifier: MPL-2.0+
# SPDX-FileCopyrightText: 2025 Max Chernoff

###############
### Imports ###
###############

from random import randint
from time import sleep
from typing import Callable, Any
from threading import Thread

#################
### Constants ###
#################

SLEEP_DURATION = 1 / 10  # seconds


############################
### Function Definitions ###
############################


def start_thread(func: Callable) -> Thread:
    """Run a function in a separate thread."""

    thread = Thread(target=func)
    thread.daemon = True
    thread.start()
    return thread


#########################
### Class Definitions ###
#########################


class Motor:
    """Controls the motor that moves the mirror."""

    def __init__(self, on_update: Callable[[float], Any]) -> None:
        self.home()
        self.on_update = on_update
        self._thread = start_thread(self._run_thread)

    def home(self) -> None:
        """Homes the motor."""
        print("Homing motor...")
        self._position = 0.0

    @property
    def position(self) -> float:
        """Gets the current position of the mirror in millimeters."""
        return self._position

    @position.setter
    def position(self, value: float) -> None:
        """Sets the position of the mirror in millimeters."""
        print(f"Setting motor position to {value} mm")
        self._target_position = value
        self._original_position = self._position

    def _run_thread(self) -> None:
        """Calls the on_update callback with the current position."""
        while True:
            sleep(SLEEP_DURATION)
            if self._position < self._target_position:
                self._position += min(
                    0.1, self._target_position - self._position
                )
            elif self._position > self._target_position:
                self._position -= min(
                    0.1, self._position - self._target_position
                )
            else:
                print("Motor reached target position.")
                break

            self.on_update(self.position)


class Detector:
    """Controls the light intensity detector."""

    def __init__(self, on_update: Callable[[int], Any]) -> None:
        self.on_update = on_update
        self._thread = start_thread(self._run_thread)

    @property
    def intensity(self) -> int:
        """Gets the current light intensity reading from the detector."""
        return randint(0, 65535)

    def _run_thread(self) -> None:
        """Calls the on_update callback with the current intensity."""
        while True:
            sleep(SLEEP_DURATION)
            self.on_update(self.intensity)
