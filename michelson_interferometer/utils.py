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

########################
### Type Definitions ###
########################

# 2-column numpy array, used for processing the data.
FloatColumns = np.ndarray[tuple, np.dtype[np.float64]]

# List of (time, value) tuples. We're using this instead of a numpy array
# because Python lists are thread-safe.
DeviceTimeValues = list[tuple[float, float]]


############################
### Function Definitions ###
############################


def start_thread(func: Callable, *args) -> Thread:
    """Run a function in a separate thread."""

    thread = Thread(target=func, args=args)
    thread.daemon = True
    thread.start()
    return thread


def by_time_to_by_position(
    detector_data: FloatColumns,
    motor_data: FloatColumns,
) -> pl.DataFrame:
    """Converts the data from time-based to position-based."""
    # Convert to Polars DataFrames
    detector = pl.DataFrame(
        detector_data, schema=["time", "intensity"]
    ).with_columns(pl.from_epoch("time", time_unit="s"))

    motor = pl.DataFrame(motor_data, schema=["time", "position"]).with_columns(
        pl.from_epoch("time", time_unit="s"),
    )

    # Join the data
    by_position = (
        motor.join_asof(
            detector,
            on="time",
            strategy="nearest",
        )
        .select(
            pl.col("position").round(3),
            pl.col("intensity"),
        )
        .group_by("position")
        .agg(pl.col("intensity"))
        .sort("position")
    )

    return by_position


def dataframe_merge_nested(data: pl.DataFrame) -> FloatColumns:
    """Merges the contents of arrays nested in columns into a single column."""
    return data.explode(
        pl.last(),  # type: ignore[arg-type]
    ).to_numpy()


def dataframe_median_nested(data: pl.DataFrame) -> FloatColumns:
    """Computes the median of arrays nested in columns."""
    return data.with_columns(pl.last().list.median()).to_numpy()


def fourier_transform(data: FloatColumns) -> tuple[FloatColumns, FloatColumns]:
    """Computes the Fourier transform of the data, returning the real and
    imaginary parts."""
    complex = np.fft.rfft(data)

    # The first element is the constant offset, which we don't care about, so
    # we'll zero it out.
    complex[0] = 0

    return complex.real, complex.imag


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
