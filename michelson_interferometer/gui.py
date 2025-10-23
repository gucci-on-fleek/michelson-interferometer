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

import numpy as np
from matplotlib.backends.backend_gtk4agg import (
    FigureCanvasGTK4Agg as FigureCanvas,
)

from . import devices, utils

# Gtk imports
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
PLOT_SCALE_FACTOR = 0.9
PLOT_UPDATE_INTERVAL = 1  # seconds
PLOT_VERTICAL_SUBTRACT = 200
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
    data_panel: Adw.ToolbarView = Gtk.Template.Child()
    detector_value: Gtk.Label = Gtk.Template.Child()
    final_position: Adw.SpinRow = Gtk.Template.Child()
    gain: Adw.SpinRow = Gtk.Template.Child()
    initial_position: Adw.SpinRow = Gtk.Template.Child()
    plot_box: Gtk.Box = Gtk.Template.Child()
    position: Adw.SpinRow = Gtk.Template.Child()
    save_as: Gtk.FileDialog = Gtk.Template.Child()
    step: Adw.SpinRow = Gtk.Template.Child()
    stop_motion_button: Gtk.Button = Gtk.Template.Child()
    speed: Adw.SpinRow = Gtk.Template.Child()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        # Register the "about" action
        self._register_about_action()

        # Initialize the devices
        self.motor = devices.Motor(
            on_update=lambda value: GLib.idle_add(self.set_position, value)
        )
        self.detector = devices.Detector(
            on_update=lambda value: GLib.idle_add(self.update_detector, value)
        )

        # Initialize the plotter
        self._initialize_plotter()

        # Initialize variables
        self.current_motion = self.stop_motion_button
        self.ignore_position_changes = False
        self.motion_thread: Thread | None = None
        self.motion_should_stop = False

        # Update the gain
        self.gain_changed(self.gain)

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

    def _initialize_plotter(self) -> None:
        """Initialize the plotter."""
        resolution = self._get_resolution()
        self.plot_width = PLOT_VERTICAL_SUBTRACT
        self.plot_height = PLOT_VERTICAL_SUBTRACT

        self.plotter = utils.Plotter(resolution)
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
        canvas.set_size_request(
            int(PLOT_SCALE_FACTOR * self.plot_width),
            int(PLOT_SCALE_FACTOR * self.plot_height),
        )
        child = self.plot_box.get_first_child()

        if child:
            self.plot_box.remove(child)
        self.plot_box.append(canvas)

        self.plot_width = self.data_panel.get_width()
        self.plot_height = self.data_panel.get_height() - PLOT_VERTICAL_SUBTRACT

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
            ) in zip(self.motor.data, self.detector.data):
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
        self.detector_value.set_label(f"{value}")


###################
### Entry Point ###
###################


def main() -> None:
    """Runs the application."""
    appplication = Application()
    appplication.run(sys.argv)


if __name__ == "__main__":
    main()
