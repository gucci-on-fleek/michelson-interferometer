# Michelson Interferometer Control Software
# https://github.com/gucci-on-fleek/michelson-interferometer
# SPDX-License-Identifier: MPL-2.0+
# SPDX-FileCopyrightText: 2025 Max Chernoff

###############
### Imports ###
###############

from typing import Any
from random import randint
from time import sleep
from collections import namedtuple

#################
### Constants ###
#################

MAX_INTENSITY = 2**16 - 1  # 16-bit detector
SHORT_SLEEP = 1 / 120  # seconds
LONG_SLEEP = 1 / 6  # seconds

#########################
### Class Definitions ###
#########################

VelocityParameters = namedtuple("VelocityParameters", ["max_velocity"])


class KinesisMotor:
    """Mock KinesisMotor for testing purposes."""

    def __init__(self, path: str, scale: tuple[float, float, float]) -> None:
        print(f"(KinesisMotor) __init__({path!r}, {scale!r})")
        self._position = 0.0
        self._speed = 0.0

    def wait_for_stop(self) -> None:
        print("(KinesisMotor) wait_for_stop()")
        sleep(LONG_SLEEP)

    def _enable_channel(self, enabled: bool) -> None:
        print(f"(KinesisMotor) _enable_channel({enabled!r})")
        sleep(SHORT_SLEEP)

    def home(self, force: bool, sync: bool) -> None:
        print(f"(KinesisMotor) home({force!r}, {sync!r})")
        sleep(SHORT_SLEEP)

    def stop(self) -> None:
        print("(KinesisMotor) stop()")
        sleep(SHORT_SLEEP)

    def get_position(self) -> float:
        # print("(KinesisMotor) get_position() -> {self._position!r}")  # Too noisy
        sleep(SHORT_SLEEP)
        return self._position

    def move_to(self, position: float) -> None:
        print(f"(KinesisMotor) move_to({position!r})")
        sleep(SHORT_SLEEP)
        self._position = position

    def setup_velocity(self, max_velocity: float, scale: bool) -> None:
        print(f"(KinesisMotor) setup_velocity({max_velocity!r}, {scale!r})")
        sleep(SHORT_SLEEP)
        self._speed = max_velocity

    def get_velocity_parameters(self, scale: bool) -> VelocityParameters:
        print(
            f"(KinesisMotor) get_velocity_parameters({scale!r}) -> {self._speed!r}"
        )
        sleep(SHORT_SLEEP)
        return VelocityParameters(max_velocity=self._speed)


class SCPIDevice:
    """Mock SCPIDevice for testing purposes."""

    def __init__(
        self, conn: tuple[str, int], timeout: float, term_write: str
    ) -> None:
        print(f"(SCPIDevice) __init__({conn!r}, {timeout!r}, {term_write!r})")

        self._gain = 0

    def get_id(self) -> str:
        print('(SCPIDevice) get_idn() -> "MOCK_DEVICE,MODEL_1234,SN0001,1.0"')
        sleep(SHORT_SLEEP)
        return "MOCK_DEVICE,MODEL_1234,SN0001,1.0"

    def ask(self, command: str, datatype: str) -> Any:
        match command:
            case "det:gain?":
                value = self._gain
            case "det:meas?":
                value = randint(0, MAX_INTENSITY)
            case _:
                raise ValueError(f"Unknown command: {command!r}")

        # print(f"(SCPIDevice) ask({command!r}, {datatype!r}) -> {value!r}")  # Too noisy
        sleep(SHORT_SLEEP)
        return value

    def write(self, command: str) -> None:
        print(f"(SCPIDevice) write({command!r})")
        sleep(SHORT_SLEEP)
        match command.split():
            case ["det:gain", value]:
                self._gain = int(value)
            case _:
                raise ValueError(f"Unknown command: {command!r}")
