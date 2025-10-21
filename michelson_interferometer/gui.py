#!/usr/bin/env python3
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
from time import time as unix_time
from typing import Callable

import gi
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_gtk4agg import (
    FigureCanvasGTK4Agg as FigureCanvas,
)
from matplotlib.figure import Figure

# from . import devices_mock as devices

from . import devices

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GObject", "2.0")

from gi.repository import Adw, Gio, GLib, GObject, Gtk  # type: ignore

#################
### Constants ###
#################

APP_NAME = "Michelson Interferometer"
APP_ID = "ca.maxchernoff.michelson_interferometer"

UI_PATH = Path(__file__).parent
PLOT_UPDATE_INTERVAL = 1  # seconds
TSV_HEADER = (
    "motor_time",
    "motor_position",
    "detector_time",
    "detector_intensity",
)


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

        self.motor = devices.Motor(
            on_update=lambda value: GLib.idle_add(self.set_position, value)
        )
        self.detector = devices.Detector(
            on_update=lambda value: GLib.idle_add(self.update_detector, value)
        )
        self.current_motion = self.stop_motion_button

        self.ignore_position_changes = False

        self.plot_width = 200
        self.plot_height = 200

        self.gain_changed(self.gain)

        start_thread(self.draw_plot)

        self.motion_thread: Thread | None = None
        self.motion_should_stop = False

    def set_position(self, value: float) -> None:
        self.ignore_position_changes = True
        self.position.set_value(value)
        self.ignore_position_changes = False

    @Gtk.Template.Callback()
    def position_changed(self, spinner: Adw.SpinRow) -> None:
        if not self.ignore_position_changes:
            value = spinner.get_value()
            self.motor.position = value

    @Gtk.Template.Callback()
    def gain_changed(self, spinner: Adw.SpinRow) -> None:
        value = spinner.get_value()
        self.detector.gain = int(value)

    @Gtk.Template.Callback()
    def home_motor(self, button: Adw.ButtonRow) -> None:  # type: ignore
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
        start_thread(
            self.do_motion,
            self.initial_position.get_value(),
            -self.step.get_value(),
        )

    @Gtk.Template.Callback()
    def step_backwards(self, button: Gtk.Button) -> None:
        self.set_current_motion(button)
        current = self.motor.position
        step = self.step.get_value()
        self.motor.position = current - step
        self.set_current_motion(self.stop_motion_button)

    @Gtk.Template.Callback()
    def stop_motion(self, button: Gtk.Button) -> None:
        self.set_current_motion(button)
        if self.motion_thread and self.motion_thread.is_alive():
            self.motion_should_stop = True
            self.motion_thread.join()
            self.motion_should_stop = False

        self.motor.stop()

    @Gtk.Template.Callback()
    def step_forwards(self, button: Gtk.Button) -> None:
        self.set_current_motion(button)
        current = self.motor.position
        step = self.step.get_value()
        self.motor.position = current + step
        self.set_current_motion(self.stop_motion_button)

    @Gtk.Template.Callback()
    def run_forwards(self, button: Gtk.Button) -> None:
        self.set_current_motion(button)
        start_thread(
            self.do_motion,
            self.final_position.get_value(),
            self.step.get_value(),
        )

    @Gtk.Template.Callback()
    def go_to_final(self, button: Gtk.Button) -> None:
        self.set_current_motion(button)
        value = self.final_position.get_value()
        self.motor.position = value
        self.set_current_motion(self.stop_motion_button)

    @Gtk.Template.Callback()
    def save_data(self, button: Adw.SplitButton) -> None:
        self.save_as.save(callback=self.on_save_dialog_response)

    def on_save_dialog_response(
        self, dialog: Gtk.FileDialog, task: Gio.Task
    ) -> None:
        file = dialog.save_finish(task)
        if file is None:
            return
        path = Path(file.get_path()).with_suffix(".tsv")  # type: ignore
        with path.open("w") as f:
            writer = csv_writer(f, dialect=excel_tab)
            writer.writerow(TSV_HEADER)
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
        self.motor.data.clear()
        self.detector.data.clear()

    def update_detector(self, value: int) -> None:
        self.detector_value.set_label(f"{value}")

    def draw_plot(self) -> None:
        while True:
            sleep(PLOT_UPDATE_INTERVAL)
            figure = Figure(
                figsize=(
                    10 * self.plot_width / self.resolution,
                    10 * self.plot_height / self.resolution,
                ),
                dpi=self.resolution,
            )
            figure.subplots_adjust(bottom=0.20, left=0.20)
            ax = figure.add_subplot()

            ax.set_xlabel("Time (s)")

            detector = np.array(self.detector.data)
            motor = np.array(self.motor.data)
            try:
                ax.plot(
                    detector[:, 0] - detector[0, 0],
                    detector[:, 1],
                    ".",
                    label="Detector",
                )
                ax.plot(
                    motor[:, 0] - motor[0, 0],
                    motor[:, 1],
                    ".",
                    label="Mirror",
                )
            except IndexError:
                continue
            figure.legend(loc="outside upper right")

            GLib.idle_add(self.render_plot, FigureCanvas(figure))

    def render_plot(self, canvas: FigureCanvas) -> None:
        canvas.set_size_request(
            int(0.9 * self.plot_width), int(0.9 * self.plot_height)
        )
        child = self.plot_box.get_first_child()
        if child:
            self.plot_box.remove(child)
        self.plot_box.append(canvas)

        self.plot_width = self.data_panel.get_width()
        self.plot_height = self.data_panel.get_height() - 200

    def do_motion(self, end: float, step: float) -> None:
        position = self.motor.position
        while (step > 0 and position < end) or (step < 0 and position > end):
            if self.motion_should_stop:
                break
            position += step
            self.motor.position = position
            self.motor.wait()


###################
### Entry Point ###
###################


def configure_matplotlib() -> None:
    plt.rcParams["font.family"] = "STIXGeneral"
    plt.rcParams["mathtext.fontset"] = "stix"
    plt.rcParams["font.size"] = 10

    # Enable the grid
    plt.rcParams["axes.grid"] = True
    plt.rcParams["axes.grid.which"] = "major"


def main() -> None:
    configure_matplotlib()
    appplication = Application()
    appplication.run(sys.argv)


if __name__ == "__main__":
    main()
