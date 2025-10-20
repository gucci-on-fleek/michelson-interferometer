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

#########################
### Class Definitions ###
#########################


class Motor:
    """Controls the motor that moves the mirror."""

    def __init__(self) -> None:
        self.home()

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
        old_position = self._position
        self._position = value
        sleep(abs(old_position - value) / 20)
        print("Motor position set.")


class Detector:
    """Controls the light intensity detector."""

    @property
    def intensity(self) -> int:
        """Gets the current light intensity reading from the detector."""
        return randint(0, 65535)
