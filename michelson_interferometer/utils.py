# Michelson Interferometer Control Software
# https://github.com/gucci-on-fleek/michelson-interferometer
# SPDX-License-Identifier: MPL-2.0+
# SPDX-FileCopyrightText: 2025 Max Chernoff

###############
### Imports ###
###############

from threading import Thread
from time import sleep
from typing import Callable
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_gtk4agg import (
    FigureCanvasGTK4Agg as FigureCanvas,
)
from matplotlib.figure import Figure

############################
### Function Definitions ###
############################


def start_thread(func: Callable, *args) -> Thread:
    """Run a function in a separate thread."""

    thread = Thread(target=func, args=args)
    thread.daemon = True
    thread.start()
    return thread


#########################
### Class Definitions ###
#########################


class Plotter:
    def __init__(
        self,
        resolution: float,
    ) -> None:
        """Configure the matplotlib settings."""
        plt.rcParams["font.family"] = "Adwaita Sans"
        plt.rcParams["font.size"] = 10

        # Enable the grid
        plt.rcParams["axes.grid"] = True
        plt.rcParams["axes.grid.which"] = "major"

        # Set the variables
        self.resolution = resolution

    def draw_plot(
        self,
        width: int,
        height: int,
        detector_data: np.ndarray,
        motor_data: np.ndarray,
    ) -> FigureCanvas | None:
        """Draw the plot and return a FigureCanvas."""

        # Create the figure and axes
        figure = Figure(
            figsize=(
                10 * width / self.resolution,
                10 * height / self.resolution,
            ),
            dpi=self.resolution,
        )
        ax1 = figure.add_subplot()
        ax2 = ax1.twinx()

        # Set the display settings
        ax1.set_xlabel("Time (s)")
        ax1.set_ylabel("Intensity")
        ax2.set_xlabel("Time (s)")
        ax2.set_ylabel("Position (mm)")
        ax2.grid(visible=False)
        figure.subplots_adjust(bottom=0.1, left=0.1)

        # Plot the data
        try:
            ax1.plot(
                detector_data[:, 0] - detector_data[0, 0],
                detector_data[:, 1],
                ".C0",
                label="Detector",
            )
            ax2.plot(
                motor_data[:, 0] - motor_data[0, 0],
                motor_data[:, 1],
                ".C1",
                label="Mirror",
            )
        except IndexError:
            return None

        # Add the legends
        figure.legend(loc="outside upper right")

        # Return the canvas
        return FigureCanvas(figure)
