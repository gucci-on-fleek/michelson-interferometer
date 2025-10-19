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

MOTOR_MIN_POS = 0.0  # millimeters
MOTOR_MAX_POS = 50.0  # millimeters
MOTOR_PRECISION = 3  # decimal places


#########################
### Class Definitions ###
#########################


class Application(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id=APP_ID,
        )
        self.connect("activate", self.on_activate)
        self._add_about()

    def on_activate(self, application):
        builder = Gtk.Builder()
        builder.add_from_file("gui.ui")

        self.window = cast(
            Adw.ApplicationWindow, builder.get_object("main_window")
        )
        self.window.set_application(application)

        self.position_slider = cast(
            Gtk.Scale, builder.get_object("position_slider")
        )
        # self.position_slider.set_format_value_func(
        #     lambda scale, value: f"{value:.{MOTOR_PRECISION}f} mm"
        # )

        self.window.present()

    def _add_about(self):
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


###################
### Entry Point ###
###################

appplication = Application()
appplication.run(sys.argv)
