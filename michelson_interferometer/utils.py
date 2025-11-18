# Michelson Interferometer Control Software
# https://github.com/gucci-on-fleek/michelson-interferometer
# SPDX-License-Identifier: MPL-2.0+
# SPDX-FileCopyrightText: 2025 Max Chernoff

###############
### Imports ###
###############

from pathlib import Path
from threading import Thread
from typing import Callable

import numpy as np
import polars as pl
from scipy import signal

########################
### Type Definitions ###
########################

# 2-column numpy array, used for processing the data.
FloatColumns = np.ndarray[tuple, np.dtype[np.float64]]

# List of (time, value) tuples. We're using this instead of a numpy array
# because Python lists are thread-safe.
DeviceTimeValues = list[tuple[float, float]]

#################
### Constants ###
#################

# Lomb–Scargle constants
BLUEST_VISIBLE_WAVELENGTH = 390e-9
FREQUENCY_TO_ANGULAR_FREQUENCY = 2.0 * np.pi
INTERFEROMETER_FREQUENCY_FACTOR = 2.0
REDDEST_VISIBLE_WAVELENGTH = 700e-9
THRESHOLD_QUANTILE = 0.90  # 90th percentile


############################
### Function Definitions ###
############################


def start_thread(func: Callable, *args) -> Thread:
    """Run a function in a separate thread."""

    thread = Thread(target=func, args=args)
    thread.daemon = True
    thread.start()
    return thread


def parse_data(
    motor_np: FloatColumns,
    detector_np: FloatColumns,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Parse the raw motor and detector data into DataFrames."""

    motor = pl.DataFrame(
        motor_np,
        schema=(("time", pl.Float64), ("position", pl.Float64)),
    ).with_columns(
        pl.col("time") - pl.col("time").min(),
    )

    detector = pl.DataFrame(
        detector_np,
        schema=(("time", pl.Float64), ("intensity", pl.Float64)),
    ).with_columns(
        pl.col("time") - pl.col("time").min(),
    )

    return motor, detector


def trim_endpoints(
    motor: pl.DataFrame,
    detector: pl.DataFrame,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Trim the endpoints of the motor data where no motion occurred."""

    last_position = motor.select(pl.col("position").last()).item()
    end_time = (
        motor.filter(
            pl.col("position") == last_position,
        )
        .select(pl.col("time"))
        .min()
        .item()
    )

    first_position = motor.select(pl.col("position").first()).item()
    start_time = (
        motor.filter(
            pl.col("position") == first_position,
        )
        .select(pl.col("time"))
        .max()
        .item()
    )

    motor = motor.filter(
        pl.col("time") >= start_time,
        pl.col("time") <= end_time,
    )
    detector = detector.filter(
        pl.col("time") >= start_time,
        pl.col("time") <= end_time,
    )
    return motor, detector


def interpolate_motion(
    motor_np: pl.DataFrame,
    detector_np: pl.DataFrame,
) -> FloatColumns:
    """Interpolate the motor positions.

    The motor rounds its position data to the nearest 0.005mm, but it moves
    smoothly between measurements. To counteract this, we will select only the
    middle point in a run of identical position measurements, and linearly interpolate between them.
    """

    motor = pl.DataFrame(
        motor_np,
        schema=(("time", pl.Float64), ("position", pl.Float64)),
    )
    detector = pl.DataFrame(
        detector_np,
        schema=(("time", pl.Float64), ("intensity", pl.Float64)),
    )

    motor, detector = trim_endpoints(motor, detector)

    midpoint_positions = (
        motor.group_by("position")
        .agg(pl.first().quantile(0.5, interpolation="nearest"))
        .sort("position")
        .select(
            pl.col("time"),
            pl.col("position"),
        )
    )

    interpolated = (
        midpoint_positions.join(
            other=detector,
            on="time",
            how="full",
            coalesce=True,
        )
        .sort("time")
        .with_columns(pl.col("position").interpolate_by("time"))
        .drop_nulls(("position", "intensity"))
    )

    return interpolated.select(
        pl.col("position"),
        pl.col("intensity"),
    ).to_numpy()


def lomb_scargle(
    distances: np.ndarray,
    intensities: np.ndarray,
    sample_count: int,
) -> tuple[FloatColumns, FloatColumns]:
    """Compute the Lomb-Scargle periodogram of the given data."""

    wavelengths = np.linspace(
        REDDEST_VISIBLE_WAVELENGTH, BLUEST_VISIBLE_WAVELENGTH, sample_count
    )

    wavenumbers = INTERFEROMETER_FREQUENCY_FACTOR / wavelengths

    spectral_power = signal.lombscargle(
        x=distances,
        y=intensities,
        freqs=wavenumbers * FREQUENCY_TO_ANGULAR_FREQUENCY,
        normalize="normalize",  # type: ignore[arg-type]
        precenter=True,
    )

    return wavelengths, spectral_power  # type: ignore[return-value]


def remove_noise_floor(
    spectral_power: np.ndarray,
) -> np.ndarray:
    """Remove the noise floor from the spectral power data."""

    threshold = np.quantile(spectral_power, THRESHOLD_QUANTILE)
    return np.clip(spectral_power - threshold, 0, None)


def save_data(
    path: Path,
    motor_data: DeviceTimeValues,
    detector_data: DeviceTimeValues,
) -> None:
    """Saves the motor and detector data to a CSV file."""
    # Create the DataFrame
    motor = pl.DataFrame(
        motor_data,
        schema=(("motor_time", pl.Float64), ("motor_position", pl.Float64)),
        orient="row",
    )
    detector = pl.DataFrame(
        detector_data,
        schema=(
            ("detector_time", pl.Float64),
            ("detector_intensity", pl.Float64),
        ),
        orient="row",
    )
    data = pl.concat([motor, detector], how="horizontal")

    # Save the data
    data.write_csv(
        path,
        include_header=True,
        line_terminator="\n",
        separator="\t",
        quote_style="never",
        null_value="null",
    )
