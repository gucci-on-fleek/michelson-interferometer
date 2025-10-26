# Michelson Interferometer Control Software
# https://github.com/gucci-on-fleek/michelson-interferometer
# SPDX-License-Identifier: MPL-2.0+
# SPDX-FileCopyrightText: 2025 Max Chernoff

###############
### Imports ###
###############

from threading import Thread
from typing import Callable

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_gtk4cairo import (
    FigureCanvasGTK4Cairo as FigureCanvas,
)

from matplotlib.figure import Figure
from matplotlib.rcsetup import cycler

########################
### Type Definitions ###
########################

type RGBAColour = tuple[float, float, float, float]


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
        get_colour: Callable[[str], RGBAColour],
        font_name: str,
        font_size: int,
        dark_mode: bool,
    ) -> None:
        """Configure the matplotlib settings."""
        # Fonts
        plt.rcParams["font.family"] = font_name
        plt.rcParams["font.size"] = font_size

        # Background colours
        bg = get_colour("window_bg_color")
        plt.rcParams["figure.facecolor"] = bg
        plt.rcParams["axes.facecolor"] = bg
        plt.rcParams["figure.edgecolor"] = bg

        # Foreground colours
        fg = get_colour("window_fg_color")
        plt.rcParams["axes.edgecolor"] = fg
        plt.rcParams["text.color"] = fg
        plt.rcParams["axes.labelcolor"] = fg
        plt.rcParams["xtick.color"] = fg
        plt.rcParams["ytick.color"] = fg

        # Frame
        plt.rcParams["axes.spines.bottom"] = True
        plt.rcParams["axes.spines.left"] = True
        plt.rcParams["axes.spines.right"] = True
        plt.rcParams["axes.spines.top"] = False

        # Enable the grid
        plt.rcParams["axes.grid"] = True
        plt.rcParams["axes.grid.which"] = "major"
        plt.rcParams["grid.alpha"] = 0.4

        # Ticks
        plt.rcParams["xtick.bottom"] = True
        plt.rcParams["ytick.left"] = True
        plt.rcParams["ytick.right"] = True
        plt.rcParams["xtick.top"] = False

        plt.rcParams["xtick.direction"] = "in"
        plt.rcParams["ytick.direction"] = "in"
        plt.rcParams["xtick.minor.visible"] = True
        plt.rcParams["ytick.minor.visible"] = True

        # Set the colour cycle
        plt.rcParams["axes.prop_cycle"] = cycler(
            color=(
                get_colour("blue_2" if dark_mode else "blue_4"),
                get_colour("orange_2" if dark_mode else "orange_4"),
            ),
        )

        # Layout
        plt.rcParams["figure.constrained_layout.use"] = True

    def draw_plot(
        self,
        detector_data: np.ndarray,
        motor_data: np.ndarray,
    ) -> FigureCanvas | None:
        """Draw the plot and return a FigureCanvas."""

        # Create the figure and axes
        figure = Figure()
        ax1 = figure.add_subplot()
        ax2 = ax1.twinx()

        # Set the display settings
        ax1.set_xlabel("Time (s)")
        ax1.set_ylabel("Intensity (%)")
        ax2.set_ylabel("Position (mm)")
        ax2.grid(visible=False)

        # Plot the data
        try:
            ax1.plot(
                detector_data[:, 0] - detector_data[0, 0],
                detector_data[:, 1] * 100,
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
