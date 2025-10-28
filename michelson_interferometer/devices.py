# Michelson Interferometer Control Software
# https://github.com/gucci-on-fleek/michelson-interferometer
# SPDX-License-Identifier: MPL-2.0+
# SPDX-FileCopyrightText: 2025 Max Chernoff

###############
### Imports ###
###############

from glob import glob
from itertools import cycle
from os import environ
from queue import Empty, Queue
from threading import Lock
from time import sleep
from time import time as unix_time
from traceback import print_exc
from typing import TYPE_CHECKING, Any, Callable
from warnings import catch_warnings

with catch_warnings(category=UserWarning, action="ignore", lineno=15):
    from pylablib.core.devio.SCPI import SCPIDevice
    from pylablib.devices.Thorlabs import KinesisMotor, ThorlabsError

from .utils import start_thread

#################
### Constants ###
#################

MOTOR_DEVICE_GLOB = "/dev/ttyUSB?"
DETECTOR_DEVICE_GLOB = "/dev/ttyACM?"

# For a KBD101/DDSM50 controller, from Thorlabs documentation:
#     https://www.thorlabs.com/Software/Motion%20Control/APT_Communications_Protocol.pdf
MOTOR_SCALE = (2_000.0, 13_421.77, 1.374)
MOTOR_MAX_POS = 50.0  # millimeters
MOTOR_MAX_SPEED = 100.0  # millimeters/second
SPEED_EPSILON = 0.1  # millimeters/second

DETECTOR_BAUD = 115_200
DETECTOR_TIMEOUT = 0.05  # seconds
DETECTOR_NL = "\n"

SLEEP_DURATION = 1 / 120  # seconds

MAX_INTENSITY = 2**16 - 1  # 16-bit detector


######################
### Initialization ###
######################

# Fake devices for testing
if (not TYPE_CHECKING) and ("MI_FAKE_DEVICES" in environ):
    from .devices_mock import SCPIDevice, KinesisMotor

    MOTOR_DEVICE_GLOB = "/dev/null"
    DETECTOR_DEVICE_GLOB = "/dev/null"

    fake_devices = True
else:
    fake_devices = False


#########################
### Class Definitions ###
#########################


class Motor:
    """Controls the motor that moves the mirror."""

    def __init__(self, on_update: Callable[[float], Any]) -> None:
        # Initialize the device
        try:
            path = glob(MOTOR_DEVICE_GLOB)[0]
        except IndexError:
            raise IOError("No motor device found")

        self._device = KinesisMotor(
            path,
            scale=MOTOR_SCALE,  # type: ignore[arg-type]
        )

        # Initialize the variables
        self.on_update = on_update
        self.data: list[tuple[float, float]] = []
        self._current_speed = 0.0

        # Initialize the thread
        self._thread = start_thread(self._run_thread)
        self._queue: Queue[
            tuple[Callable[[float], None], float]
            | tuple[Callable[[None], None], None]
        ] = Queue()

        # Home the motor at startup
        self.home()

    def wait(self) -> None:
        """Waits for the motor to finish any current movement."""
        sleep(2 * SLEEP_DURATION)
        try:
            self._device.wait_for_stop()
        except ThorlabsError:
            # Try once more
            sleep(2 * SLEEP_DURATION)
            self._device.wait_for_stop()

    def home(self) -> None:
        """Homes the motor."""
        self._queue.put((self._enable, None))
        self._queue.put((self._set_speed, MOTOR_MAX_SPEED))
        self._queue.put((self._home, None))

    def _enable(self, _: None) -> None:
        self._device._enable_channel(enabled=True)

    def _home(self, _: None) -> None:
        self._device.home(force=True, sync=False)

    def stop(self) -> None:
        """Stops the motor."""
        self._queue.put((self._stop, None))
        self._queue.put((self._set_speed, MOTOR_MAX_SPEED))

    def _stop(self, _: None) -> None:
        self._device.stop()

    @property
    def position(self) -> float:
        """Gets the current position of the mirror in millimeters."""
        try:
            return self.data[-1][1]
        except IndexError:
            sleep(2 * SLEEP_DURATION)
            return self.data[-1][1]

    def _get_position(self, _: None) -> None:
        """Gets the current position of the mirror and calls on_update."""
        position = self._device.get_position()
        self.data.append((unix_time(), position))
        self.on_update(position)

    def set_position(
        self, position: float, speed: float = MOTOR_MAX_SPEED
    ) -> None:
        """Sets the position of the mirror in millimeters at a given speed."""
        if speed != self._current_speed:
            self._queue.put((self._set_speed, speed))
        self._queue.put((self._set_position, position))

    def _set_position(self, position: float) -> None:
        self._device.move_to(position)

    def _set_speed(self, speed: float) -> None:
        """Sets the speed of the motor in millimeters/second."""
        self._current_speed = speed
        for _ in range(3):
            try:
                self._device.setup_velocity(max_velocity=speed, scale=True)

                current_speed = self._device.get_velocity_parameters(
                    scale=True
                ).max_velocity

                if abs(current_speed - speed) > SPEED_EPSILON:
                    raise ValueError("Speed not set correctly")
            except (ThorlabsError, ValueError):
                sleep(SLEEP_DURATION)
            else:
                break

    def _run_thread(self) -> None:
        """Runs the thread."""

        # Every second cycle, run a command from the queue. Otherwise, get the
        # current position.
        for should_get_position in cycle([True, False]):
            sleep(SLEEP_DURATION)
            if should_get_position:
                func, arg = self._get_position, None
            else:
                try:
                    func, arg = self._queue.get_nowait()
                except Empty:
                    pass

            try:
                func(arg)  # type: ignore[arg-type]
            except:
                print_exc()


class Detector:
    """Controls the light intensity detector."""

    def __init__(self, on_update: Callable[[float], Any]) -> None:
        # Initialize the device
        try:
            path = glob(DETECTOR_DEVICE_GLOB)[0]
        except IndexError:
            raise IOError("No detector device found")

        self._device = SCPIDevice(
            (path, DETECTOR_BAUD),
            timeout=DETECTOR_TIMEOUT,
            term_write=DETECTOR_NL,
        )

        # Initialize the variables
        self.on_update = on_update
        self.data: list[tuple[float, float]] = []

        # Initialize the thread
        self._lock = Lock()
        self._thread = start_thread(self._run_thread)

        # Verify connection
        if not self._device.get_id():
            raise IOError("Failed to connect to detector")

    @property
    def gain(self) -> int:
        """Gets the current position of the mirror in millimeters."""
        with self._lock:
            value = self._device.ask("det:gain?", "int")

        assert isinstance(value, int)
        return value

    @gain.setter
    def gain(self, value: int) -> None:
        """Sets the position of the mirror in millimeters."""
        with self._lock:
            self._device.write(f"det:gain {value}")

    @property
    def intensity(self) -> float:
        """Gets the current light intensity reading from the detector."""
        with self._lock:
            value = self._device.ask("det:meas?", "int")

        assert isinstance(value, int)
        return value / MAX_INTENSITY

    def _run_thread(self) -> None:
        """Calls the on_update callback with the current intensity."""
        while True:
            sleep(SLEEP_DURATION)

            try:
                intensity = self.intensity
            except:
                print_exc()
                continue

            self.data.append((unix_time(), intensity))
            self.on_update(intensity)
