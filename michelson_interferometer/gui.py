#!/usr/bin/env python3
# Michelson Interferometer Control Software
# https://github.com/gucci-on-fleek/michelson-interferometer
# SPDX-License-Identifier: MPL-2.0+
# SPDX-FileCopyrightText: 2025 Max Chernoff

###############
### Imports ###
###############

import sys
from pathlib import Path

import gi
from matplotlib.backends.backend_gtk4agg import (
    FigureCanvasGTK4Agg as FigureCanvas,
)
from matplotlib.figure import Figure

from . import devices_mock as devices

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # type: ignore

#################
### Constants ###
#################

APP_NAME = "Michelson Interferometer"
APP_ID = "ca.maxchernoff.michelson_interferometer"

UI_PATH = Path(__file__).parent


#########################
### Class Definitions ###
#########################


class Application(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID)
        GLib.set_prgname(APP_NAME)

    def do_activate(self) -> None:
        self.window = MainWindow(application=self)
        self.window.present()


@Gtk.Template(filename=str(UI_PATH / "main.ui"))
class MainWindow(Adw.ApplicationWindow):
    __gtype_name__ = "MainWindow"

    about_dialog: Gtk.AboutDialog = Gtk.Template.Child()
    data_panel: Adw.ToolbarView = Gtk.Template.Child()
    final_position: Adw.SpinRow = Gtk.Template.Child()
    initial_position: Adw.SpinRow = Gtk.Template.Child()
    position_plot_box: Gtk.Box = Gtk.Template.Child()
    position: Adw.SpinRow = Gtk.Template.Child()
    save_as: Gtk.FileDialog = Gtk.Template.Child()
    stop_motion_button: Gtk.Button = Gtk.Template.Child()
    value_plot_box: Gtk.Box = Gtk.Template.Child()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        action = Gio.SimpleAction.new("about", None)
        action.connect(
            "activate", lambda action, param: self.about_dialog.present()
        )
        self.add_action(action)

        display = self.get_display()
        screen = display.get_monitors()[0]
        self.resolution: float = screen.get_scale() * 96  # type: ignore

        self.motor = devices.Motor()
        self.detector = devices.Detector()
        self.current_motion = self.stop_motion_button

    def draw_plot(self) -> None:
        # TODO!
        figure = Figure(figsize=(1, 1), dpi=self.resolution)
        ax = figure.add_subplot()

        ax.set_title("Interferometer Value")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Value (arb. units)")
        ax.plot([0, 1, 2, 3], [0, 1, 2, 3])

        canvas = FigureCanvas(figure)
        width = self.data_panel.get_width()
        canvas.set_size_request(int(0.9 * width), int(0.9 * width))

        child = self.value_plot_box.get_first_child()
        if child:
            self.value_plot_box.remove(child)
        self.value_plot_box.append(canvas)

    @Gtk.Template.Callback()
    def position_changed(self, spinner: Adw.SpinRow) -> None:
        value = spinner.get_value()
        self.motor.position = value

    @Gtk.Template.Callback()
    def gain_changed(self, spinner: Adw.SpinRow) -> None:
        value = spinner.get_value()
        print(f"Gain changed to: {value}")  # TODO!

    @Gtk.Template.Callback()
    def home_motor(self, button: Gtk.Button) -> None:  # type: ignore
        self.motor.home()

    def set_current_motion(self, motion: Gtk.Button) -> None:
        self.current_motion.remove_css_class("suggested-action")
        motion.add_css_class("suggested-action")
        self.current_motion = motion

    @Gtk.Template.Callback()
    def go_to_initial(self, button: Gtk.Button) -> None:
        self.set_current_motion(button)
        value = self.initial_position.get_value()
        self.motor.position = value
        self.set_current_motion(self.stop_motion_button)

    @Gtk.Template.Callback()
    def run_backwards(self, button: Gtk.Button) -> None:
        self.set_current_motion(button)
        print("Running backwards...")  # TODO!

    @Gtk.Template.Callback()
    def step_backwards(self, button: Gtk.Button) -> None:
        self.set_current_motion(button)
        current = self.motor.position
        step = self.position.get_value()
        self.motor.position = current - step
        self.set_current_motion(self.stop_motion_button)

    @Gtk.Template.Callback()
    def stop_motion(self, button: Gtk.Button) -> None:
        self.set_current_motion(button)
        print("Stopping motion...")  # TODO!

    @Gtk.Template.Callback()
    def step_forwards(self, button: Gtk.Button) -> None:
        self.set_current_motion(button)
        current = self.motor.position
        step = self.position.get_value()
        self.motor.position = current + step
        self.set_current_motion(self.stop_motion_button)

    @Gtk.Template.Callback()
    def run_forwards(self, button: Gtk.Button) -> None:
        self.set_current_motion(button)
        print("Running forwards...")  # TODO!

    @Gtk.Template.Callback()
    def go_to_final(self, button: Gtk.Button) -> None:
        self.set_current_motion(button)
        value = self.final_position.get_value()
        self.motor.position = value
        self.set_current_motion(self.stop_motion_button)

    @Gtk.Template.Callback()
    def save_data(self, button: Adw.SplitButton) -> None:
        self.save_as.open()
        print("Saving data...")  # TODO!

    @Gtk.Template.Callback()
    def clear_data(self, button: Gtk.Button) -> None:
        print("Clearing data...")  # TODO!


###################
### Entry Point ###
###################


def main() -> None:
    appplication = Application()
    appplication.run(sys.argv)


if __name__ == "__main__":
    main()
