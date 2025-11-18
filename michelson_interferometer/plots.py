# Michelson Interferometer Control Software
# https://github.com/gucci-on-fleek/michelson-interferometer
# SPDX-License-Identifier: MPL-2.0+
# SPDX-FileCopyrightText: 2025 Max Chernoff

###############
### Imports ###
###############

from math import ceil

import matplotlib.pyplot as plt
import matplotlib.style as mplstyle
from matplotlib.backends.backend_gtk4agg import (
    FigureCanvasGTK4Agg as FigureCanvas,
)
from matplotlib.figure import Figure
from matplotlib.rcsetup import cycler

from . import utils

# GTK imports
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gtk  # type: ignore

########################
### Type Definitions ###
########################

RGBAColour = tuple[float, float, float, float]


#################
### Constants ###
#################

MAX_PLOT_POINTS = 1_000
PLOT_COLOUR_NAMES = ("BLUE", "ORANGE")
TRANSPARENT_COLOUR: RGBAColour = (0.0, 0.0, 0.0, 0.0)


############################
### Function Definitions ###
############################


def gdk_colour_to_tuple(gdk_colour: Gdk.RGBA) -> RGBAColour:
    """Gets the RGBA tuple for a GDK colour."""

    return (
        gdk_colour.red,
        gdk_colour.green,
        gdk_colour.blue,
        gdk_colour.alpha,
    )


#########################
### Class Definitions ###
#########################


class Plotter:
    """Class to handle matplotlib plotting in the GUI."""

    def __init__(
        self,
        plot_mode: Adw.ToggleGroup,  # type: ignore
    ) -> None:
        """Configure the matplotlib settings."""
        # Set the matplotlib parameters
        self._set_font()
        self._set_background_colour()
        self._set_foreground_colour(plot_mode)
        self._set_grid()
        self._set_plot_colours()
        mplstyle.use("fast")

        # Use a sensible layout rather than the horrible default
        plt.rcParams["figure.constrained_layout.use"] = True

        # Variables
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.plot_mode = plot_mode

    def _set_font(self) -> None:
        """Set the matplotlib font parameters."""
        # Get the font name and size
        adw_style = Adw.StyleManager.get_default()

        name_and_size: str = adw_style.get_document_font_name()  # type: ignore
        name, size = name_and_size.rsplit(" ", 1)

        # Set the font parameters
        plt.rcParams["font.family"] = name
        plt.rcParams["font.size"] = int(size)

    def _set_background_colour(self) -> None:
        """Set the background colour of the matplotlib plots."""
        # Set the background of the matplotlib canvas to be transparent
        css = Gtk.CssProvider()
        css.load_from_string(
            ".matplotlib-canvas { background-color: transparent; }"
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),  # type: ignore
            css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1,
        )

        # Set the figure and axes backgrounds to be transparent
        plt.rcParams["figure.facecolor"] = TRANSPARENT_COLOUR
        plt.rcParams["axes.facecolor"] = TRANSPARENT_COLOUR

    def _set_foreground_colour(self, window: Adw.ApplicationWindow) -> None:
        """Set the foreground colour of the matplotlib plots."""
        # Get the text colour
        text_colour = gdk_colour_to_tuple(window.get_color())

        # Set the colours
        plt.rcParams["axes.edgecolor"] = text_colour
        plt.rcParams["text.color"] = text_colour
        plt.rcParams["axes.labelcolor"] = text_colour
        plt.rcParams["xtick.color"] = text_colour
        plt.rcParams["ytick.color"] = text_colour

    def _set_grid(self) -> None:
        """Set the grid parameters."""
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

    def _set_plot_colours(self) -> None:
        """Set the plot colours based on the current theme."""
        # See if dark mode is enabled or not
        adw_style = Adw.StyleManager.get_default()
        dark_mode = adw_style.get_dark()

        # Get the plot colours
        plot_colours: list[RGBAColour] = []
        for colour_name in PLOT_COLOUR_NAMES:
            colour_enum = getattr(Adw.AccentColor, colour_name)  # type: ignore
            gdk_colour: Gdk.RGBA = Adw.AccentColor.to_standalone_rgba(  # type: ignore
                colour_enum, dark_mode
            )
            plot_colours.append(gdk_colour_to_tuple(gdk_colour))

        plt.rcParams["axes.prop_cycle"] = cycler(color=plot_colours)

    def draw_time_plots(
        self,
        detector_data: utils.FloatColumns,
        motor_data: utils.FloatColumns,
        plot_spacing: int,
    ) -> None:
        """Draw the data as a function of time on the figure."""
        # Create the axes
        intensity_axis = self.figure.add_subplot()
        position_axis = intensity_axis.twinx()

        # Set the display settings
        intensity_axis.set_xlabel("Time (s)")
        intensity_axis.set_ylabel("Intensity (%)")
        position_axis.set_ylabel("Position (mm)")
        position_axis.grid(visible=False)

        # Plot the data
        try:
            intensity_axis.plot(
                detector_data[:, 0] - detector_data[0, 0],
                detector_data[:, 1] * 100,
                ".C0",
                label="Detector",
                markevery=plot_spacing,
            )
            position_axis.plot(
                motor_data[:, 0] - motor_data[0, 0],
                motor_data[:, 1],
                ".C1",
                label="Mirror",
                markevery=plot_spacing,
            )
        except IndexError:
            pass

    def draw_distance_plots(
        self,
        detector_data: utils.FloatColumns,
        motor_data: utils.FloatColumns,
        plot_spacing: int,
    ) -> None:
        """Draw the data as a function of distance on the figure."""
        by_position = utils.dataframe_merge_nested(
            utils.by_time_to_by_position(detector_data, motor_data)
        )

        # Create the axis
        intensity_axis = self.figure.add_subplot()

        # Set the display settings
        intensity_axis.set_xlabel("Position (mm)")
        intensity_axis.set_ylabel("Intensity (%)")

        # Plot the data
        intensity_axis.plot(
            by_position[:, 0],
            by_position[:, 1] * 100,
            ".C0",
            label="Intensity",
            markevery=plot_spacing,
        )

    def draw_fft_time_plots(
        self,
        detector_data: utils.FloatColumns,
        motor_data: utils.FloatColumns,
        plot_spacing: int,
    ) -> None:
        """Draw the data as a function of time, using a Fourier transform."""
        # Compute the FFTs
        real, imag = utils.fourier_transform(detector_data[:, 1] * 100)

        # Create the axis
        intensity_axis = self.figure.add_subplot()

        # Set the display settings
        intensity_axis.set_xlabel("Frequency (Hz)")
        intensity_axis.set_ylabel("Intensity (%)")

        # Plot the data
        intensity_axis.plot(
            real,
            ".C0",
            label="Real",
            markevery=plot_spacing,
        )
        intensity_axis.plot(
            imag,
            ".C1",
            label="Imaginary",
            markevery=plot_spacing,
        )

    def draw_fft_distance_plots(
        self,
        detector_data: utils.FloatColumns,
        motor_data: utils.FloatColumns,
        plot_spacing: int,
    ) -> None:
        """Draw the data as a function of distance, using a Fourier transform."""
        by_position = utils.dataframe_median_nested(
            utils.by_time_to_by_position(detector_data, motor_data)
        )

        # Compute the FFTs
        real, imag = utils.fourier_transform(by_position[:, 1] * 100)

        # Create the axis
        intensity_axis = self.figure.add_subplot()

        # Set the display settings
        intensity_axis.set_xlabel("Wavenumber (1/mm)")
        intensity_axis.set_ylabel("Intensity (%)")

        # Plot the data
        intensity_axis.plot(
            real,
            ".C0",
            label="Real",
            markevery=plot_spacing,
        )
        intensity_axis.plot(
            imag,
            ".C1",
            label="Imaginary",
            markevery=plot_spacing,
        )

    def draw_plot(
        self,
        detector_data: utils.FloatColumns,
        motor_data: utils.FloatColumns,
    ) -> None:
        """Redraw the plot with the given data."""

        # Create the figure and axes
        self.figure.clear(keep_observers=True)

        # Determine the plot spacing
        num_points = max(len(detector_data), len(motor_data))
        plot_spacing = max(1, ceil(num_points / MAX_PLOT_POINTS))
        print(f"Plot spacing: {plot_spacing}")
        print(f"Number of points: {num_points // plot_spacing}")

        # Draw the data
        plot_mode: str = self.plot_mode.get_active_name()
        match plot_mode:
            case "time":
                plot_func = self.draw_time_plots
            case "distance":
                plot_func = self.draw_distance_plots
            case "fourier_time":
                plot_func = self.draw_fft_time_plots
            case "fourier_distance":
                plot_func = self.draw_fft_distance_plots
            case _:
                raise ValueError(f"Unknown plot mode: {plot_mode}")
        plot_func(detector_data, motor_data, plot_spacing)

        # Add the legends
        legend = self.figure.legend(loc="outside upper right")

        # Ugh, we can't set this properly via rcParams
        legend.get_frame().set_alpha(None)
        legend.get_frame().set_facecolor(TRANSPARENT_COLOUR)

        # Redraw the canvas
        self.canvas.draw()
