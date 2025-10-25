# Michelson Interferometer Control Software
# https://github.com/gucci-on-fleek/michelson-interferometer
# SPDX-License-Identifier: MPL-2.0+
# SPDX-FileCopyrightText: 2025 Max Chernoff

###############
### Imports ###
###############

import sys
from csv import excel_tab
from csv import writer as csv_writer
from pathlib import Path
from threading import Thread
from time import sleep
from warnings import catch_warnings
from itertools import zip_longest

import numpy as np
from matplotlib.backends.backend_gtk4agg import (
    FigureCanvasGTK4Agg as FigureCanvas,
)

from . import devices, utils

# GTK imports
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk  # type: ignore

#################
### Constants ###
#################

APP_NAME = "Michelson Interferometer"
APP_ID = "ca.maxchernoff.michelson_interferometer"

UI_PATH = Path(__file__).parent
PLOT_UPDATE_INTERVAL = 1.0  # seconds
TSV_HEADER = (
    "motor_time",
    "motor_position",
    "detector_time",
    "detector_intensity",
)


#########################
### Class Definitions ###
#########################


class Application(Adw.Application):
    """The top-level application."""

    def __init__(self) -> None:
        super().__init__(application_id=APP_ID)
        GLib.set_prgname(APP_NAME)

    def do_activate(self) -> None:
        self.window = MainWindow(application=self)
        self.window.present()


@Gtk.Template(filename=str(UI_PATH / "main.ui"))
class MainWindow(Adw.ApplicationWindow):
    """The main (and only) window of the application."""

    __gtype_name__ = "MainWindow"

    # UI Elements
    about_dialog: Adw.AboutDialog = Gtk.Template.Child()
    detector_value: Gtk.Label = Gtk.Template.Child()
    device_error_dialog: Adw.AlertDialog = Gtk.Template.Child()
    final_position: Adw.SpinRow = Gtk.Template.Child()
    gain: Adw.SpinRow = Gtk.Template.Child()
    initial_position: Adw.SpinRow = Gtk.Template.Child()
    plot_bin: Adw.Bin = Gtk.Template.Child()
    position: Adw.SpinRow = Gtk.Template.Child()
    save_as: Gtk.FileDialog = Gtk.Template.Child()
    speed: Adw.SpinRow = Gtk.Template.Child()
    step: Adw.SpinRow = Gtk.Template.Child()
    stop_motion_button: Gtk.Button = Gtk.Template.Child()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        # Register the "about" action
        self._register_about_action()

        # Initialize the devices
        try:
            self.motor = devices.Motor(
                on_update=lambda value: GLib.idle_add(self.set_position, value)
            )
            self.detector = devices.Detector(
                on_update=lambda value: GLib.idle_add(
                    self.update_detector, value
                )
            )
        except:
            self.device_error_dialog.present()
            raise

        # Initialize the plotter
        self._initialize_plotter()

        # Initialize variables
        self.current_motion = self.stop_motion_button
        self.ignore_position_changes = False
        self.motion_thread: Thread | None = None
        self.motion_should_stop = False

        # Update the gain
        self.gain_changed(self.gain)

    @Gtk.Template.Callback()
    def device_error_dialog_exit(self, *_) -> None:
        """Quit the application."""
        application = self.get_application()
        assert application is not None
        application.quit()

    def _register_about_action(self) -> None:
        """Register the "about" action."""
        action = Gio.SimpleAction.new("about", None)
        action.connect(
            "activate", lambda action, param: self.about_dialog.present()
        )
        self.add_action(action)

    def _get_resolution(self) -> float:
        """Initialize the display resolution."""
        display = self.get_display()
        screen = display.get_monitors()[0]
        return screen.get_scale() * 96  # type: ignore

    def _get_colour(self, colour_name: str) -> utils.RGBAColour:
        """Gets the RGBA tuple for a given colour name from the theme."""
        with catch_warnings(category=DeprecationWarning, action="ignore"):
            style = self.get_style_context()
            gdk_colour = style.lookup_color(colour_name)[1]

        return (
            gdk_colour.red,
            gdk_colour.green,
            gdk_colour.blue,
            gdk_colour.alpha,
        )

    def _initialize_plotter(self) -> None:
        """Initialize the plotter."""
        resolution = self._get_resolution()
        self.plot_width = 200
        self.plot_height = 200

        adw_style = Adw.StyleManager.get_default()
        font_and_size: str = adw_style.get_document_font_name()  # type: ignore
        font, size = font_and_size.rsplit(" ", 1)
        dark_mode = adw_style.get_dark()

        self.plotter = utils.Plotter(
            resolution=resolution,
            get_colour=self._get_colour,
            font_name=font,
            font_size=int(size),
            dark_mode=dark_mode,
        )
        utils.start_thread(self._plot_thread)

    def _plot_thread(self) -> None:
        """Thread that continuously updates the plot."""
        while True:
            sleep(PLOT_UPDATE_INTERVAL)
            figure = self.plotter.draw_plot(
                self.plot_width,
                self.plot_height,
                np.array(self.detector.data),
                np.array(self.motor.data),
            )

            if figure is not None:
                GLib.idle_add(self.render_plot, figure)

    def render_plot(self, canvas: FigureCanvas) -> None:
        """Render the plot in the GUI, from the main thread."""
        self.plot_bin.set_child(canvas)

        self.plot_width = self.plot_bin.get_width()
        self.plot_height = self.plot_bin.get_height()

    def set_position(self, value: float) -> None:
        """Set the position spinner value."""
        self.ignore_position_changes = True
        self.position.set_value(value)
        self.ignore_position_changes = False

    @Gtk.Template.Callback()
    def position_changed(self, spinner: Adw.SpinRow) -> None:
        """Handle changes to the position spinner."""
        if not self.ignore_position_changes:
            value = spinner.get_value()
            self.motor.set_position(value)

    @Gtk.Template.Callback()
    def gain_changed(self, spinner: Adw.SpinRow) -> None:
        """Handle changes to the gain spinner."""
        value = spinner.get_value()
        self.detector.gain = int(value)

    @Gtk.Template.Callback()
    def home_motor(self, button: Adw.ButtonRow) -> None:  # type: ignore
        """Handle the "Home Motor" button press."""
        self.motor.home()

    def set_current_motion(self, motion: Gtk.Button) -> None:
        """Update the current motion button styling."""
        self.current_motion.remove_css_class("suggested-action")
        motion.add_css_class("suggested-action")
        self.current_motion = motion

    @Gtk.Template.Callback()
    def go_to_initial(self, button: Gtk.Button) -> None:
        """Handle the "Go to Initial Position" button press."""
        self.set_current_motion(button)

        value = self.initial_position.get_value()
        self.motor.set_position(value)

        self.set_current_motion(self.stop_motion_button)

    @Gtk.Template.Callback()
    def run_backwards(self, button: Gtk.Button) -> None:
        """Handle the "Run Backwards" button press."""
        self.set_current_motion(button)

        self.motion_thread = utils.start_thread(
            self._go_with_speed,
            self.initial_position.get_value(),
            self.speed.get_value(),
        )

    @Gtk.Template.Callback()
    def step_backwards(self, button: Gtk.Button) -> None:
        """Handle the "Step Backwards" button press."""
        self.set_current_motion(button)

        current = self.motor.position
        step = self.step.get_value()
        self.motor.set_position(current - step)

        self.set_current_motion(self.stop_motion_button)

    @Gtk.Template.Callback()
    def stop_motion(self, button: Gtk.Button) -> None:
        """Handle the "Stop Motion" button press."""
        self.set_current_motion(button)

        self.motor.stop()

    @Gtk.Template.Callback()
    def step_forwards(self, button: Gtk.Button) -> None:
        """Handle the "Step Forwards" button press."""
        self.set_current_motion(button)

        current = self.motor.position
        step = self.step.get_value()
        self.motor.set_position(current + step)

        self.set_current_motion(self.stop_motion_button)

    @Gtk.Template.Callback()
    def run_forwards(self, button: Gtk.Button) -> None:
        """Handle the "Run Forwards" button press."""
        self.set_current_motion(button)

        self.motion_thread = utils.start_thread(
            self._go_with_speed,
            self.final_position.get_value(),
            self.speed.get_value(),
        )

    @Gtk.Template.Callback()
    def go_to_final(self, button: Gtk.Button) -> None:
        """Handle the "Go to Final Position" button press."""
        self.set_current_motion(button)

        value = self.final_position.get_value()
        self.motor.set_position(value)

        self.set_current_motion(self.stop_motion_button)

    def _go_with_speed(self, end: float, speed: float) -> None:
        """Thread that moves the motor to a position at a given speed."""
        self.motor.set_position(end, speed)
        self.motor.wait()
        GLib.idle_add(self.set_current_motion, self.stop_motion_button)

    @Gtk.Template.Callback()
    def save_data(self, button: Adw.SplitButton) -> None:
        """Handle the "Save Data" button press."""
        self.save_as.save(callback=self.on_save_dialog_response)

    def on_save_dialog_response(
        self, dialog: Gtk.FileDialog, task: Gio.Task
    ) -> None:
        """Handle the save dialog response."""

        # Get the response from the dialog
        file = dialog.save_finish(task)
        if file is None:
            return

        # Make sure that the file has a .tsv extension
        path = Path(file.get_path()).with_suffix(".tsv")  # type: ignore

        # Open the file and write the data
        with path.open("w") as f:
            writer = csv_writer(f, dialect=excel_tab)

            # Write the header
            writer.writerow(TSV_HEADER)

            # Write the data
            for (motor_time, motor_position), (
                detector_time,
                detector_intensity,
            ) in zip_longest(self.motor.data, self.detector.data):
                writer.writerow(
                    (
                        motor_time,
                        motor_position,
                        detector_time,
                        detector_intensity,
                    )
                )

    @Gtk.Template.Callback()
    def clear_data(self, button: Gtk.Button) -> None:
        """Handle the "Clear Data" button press."""
        self.motor.data.clear()
        self.detector.data.clear()

    def update_detector(self, value: int) -> None:
        """Callback function to update the detector value display."""
        self.detector_value.set_label(f"{value * 100:7.03f}%")


###################
### Entry Point ###
###################


def main() -> None:
    """Runs the application."""
    appplication = Application()
    appplication.run(sys.argv)


if __name__ == "__main__":
    main()
