#!/usr/bin/env python3
# Michelson Interferometer Control Software
# https://github.com/gucci-on-fleek/michelson-interferometer
# SPDX-License-Identifier: MPL-2.0+
# SPDX-FileCopyrightText: 2025 Max Chernoff

###############
### Imports ###
###############

import sys
from glob import glob

try:
    # from pylablib.devices.Thorlabs import KinesisMotor
    # from pylablib.core.devio.SCPI import SCPIDevice
    pass
except ModuleNotFoundError:
    print(
        """Required modules not installed. Please install the necessary
modules using the following command:

    pip3 install .
"""
    )
    exit(1)


##################
### GUI Import ###
##################

if sys.version_info >= (3, 13):
    # Horrible monkey-patching

    import types

    sys.modules["imghdr"] = types.ModuleType("imghdr")

    from appJar import gui

    def monkey_patch_exec(str):
        exec(str, locals=gui._buildConfigFuncs.__globals__)

    gui._buildConfigFuncs.__globals__["exec"] = monkey_patch_exec
else:
    from appJar import gui


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
DETECTOR_TIMEOUT = 0.1  # seconds
DETECTOR_NL = "\n"

EM_SIZE = 24  # pixels


#########################
### Class Definitions ###
#########################


class Motor:
    """Controls the motor that moves the mirror."""

    def __init__(self) -> None:
        try:
            path = glob(MOTOR_DEVICE_GLOB)[0]
        except IndexError:
            raise IOError("No motor device found")

        self._device = KinesisMotor(
            path,
            scale=MOTOR_SCALE,  # type: ignore[arg-type]
        )

        self._device.home(sync=True, force=True)

    @property
    def position(self) -> float:
        """Gets the current position of the mirror in millimeters."""
        return self._device.get_position()

    @position.setter
    def position(self, value: float) -> None:
        """Sets the position of the mirror in millimeters."""
        self._device.move_to(value)
        self._device.wait_move()


class Detector:
    """Controls the light intensity detector."""

    def __init__(self) -> None:
        try:
            path = glob(DETECTOR_DEVICE_GLOB)[0]
        except IndexError:
            raise IOError("No detector device found")

        self._device = SCPIDevice(
            (path, DETECTOR_BAUD),
            timeout=DETECTOR_TIMEOUT,
            term_write=DETECTOR_NL,
        )

        assert self._device.get_id()

    @property
    def intensity(self) -> int:
        """Gets the current light intensity reading from the detector."""
        value = self._device.ask("det:meas?", "int")
        assert isinstance(value, int)
        return value


###########
### GUI ###
###########


def main():
    with gui("Michelson Interferometer", useTtk=True) as app:
        app.ttkStyle.configure(
            ".",
            font=("Helvetica", EM_SIZE),
            # padding=[EM_SIZE] * 4,
        )
        app.setStretch("both")
        app.setSticky("nw")

        with app.labelFrame("Motor"):
            app.addLabelScale("Position")
            app.setScaleRange("Position", 0, MOTOR_MAX_POS)
            app.setScaleIncrement("Position", 0.01)


if __name__ == "__main__":
    main()
