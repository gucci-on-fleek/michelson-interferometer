#!/usr/bin/env python3
# Michelson Interferometer Control Software
# https://github.com/gucci-on-fleek/michelson-interferometer
# SPDX-License-Identifier: MPL-2.0+
# SPDX-FileCopyrightText: 2025 Max Chernoff

###############
### Imports ###
###############

import sys

try:
    from pylablib.devices import Thorlabs
    from pylablib.core.devio import SCPI
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
SENSOR_DEVICE_GLOB = "/dev/ttyACM?"

# For a KBD101/DDSM50 controller, from Thorlabs documentation:
#     https://www.thorlabs.com/Software/Motion%20Control/APT_Communications_Protocol.pdf
MOTOR_SCALE = (2_000, 13_421.77, 1.374)


############################
### Function Definitions ###
############################


###########
### GUI ###
###########

if __name__ == "__main__":
    with gui("Hello, world!") as app:
        app.addLabel("title", "Hello, world!")
