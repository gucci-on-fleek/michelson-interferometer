#!/usr/bin/env python3
# Michelson Interferometer Control Software
# https://github.com/gucci-on-fleek/michelson-interferometer
# SPDX-License-Identifier: MPL-2.0+
# SPDX-FileCopyrightText: 2025 Max Chernoff

###############
### Imports ###
###############

import sys
from typing import cast
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # type: ignore

#################
### Constants ###
#################

APP_NAME = "Michelson Interferometer"
APP_ID = "ca.maxchernoff.michelson_interferometer"
APP_VERSION = "0.0"
APP_WEBSITE = "https://github.com/gucci-on-fleek/michelson-interferometer"

UI_PATH = Path(__file__).parent


#########################
### Class Definitions ###
#########################


class Application(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID)
        GLib.set_prgname(APP_NAME)

        self._add_about()

    def do_activate(self) -> None:
        self.window = MainWindow(application=self)
        self.window.present()

    def _add_about(self) -> None:
        self.about = Adw.AboutDialog(
            application_name=APP_NAME,
            developer_name="Max Chernoff",
            version=APP_VERSION,
            license_type=Gtk.License.MPL_2_0,
            website=APP_WEBSITE,
        )
        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", lambda action, param: self.about.present())
        self.add_action(action)


@Gtk.Template(filename=str(UI_PATH / "main.ui"))
class MainWindow(Adw.ApplicationWindow):
    __gtype_name__ = "MainWindow"

    position: Adw.SpinRow = Gtk.Template.Child()
    save_as: Gtk.FileDialog = Gtk.Template.Child()

    @Gtk.Template.Callback()
    def position_changed(self, spinner: Adw.SpinRow) -> None:
        value = spinner.get_value()
        print(f"Position changed to: {value}")  # TODO!

    @Gtk.Template.Callback()
    def gain_changed(self, spinner: Adw.SpinRow) -> None:
        value = spinner.get_value()
        print(f"Gain changed to: {value}")  # TODO!

    @Gtk.Template.Callback()
    def home_motor(self, button: Adw.ButtonRow) -> None:  # type: ignore
        print("Homing motor...")  # TODO!

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

appplication = Application()
appplication.run(sys.argv)
