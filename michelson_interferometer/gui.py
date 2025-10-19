#!/usr/bin/env python3
# Michelson Interferometer Control Software
# https://github.com/gucci-on-fleek/michelson-interferometer
# SPDX-License-Identifier: MPL-2.0+
# SPDX-FileCopyrightText: 2025 Max Chernoff

###############
### Imports ###
###############

import sys

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


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.initialize_window()
        self.add_header()

        self.add_motor_controls()

    def initialize_window(self):
        self.set_title(APP_NAME)
        GLib.set_application_name(APP_NAME)

        self.content = Adw.ToolbarView()
        self.set_content(self.content)

    def add_header(self):
        self.header = Adw.HeaderBar()
        self.content.add_top_bar(self.header)

        # Create a popover
        self.menu = Gio.Menu.new()
        self.popover = Gtk.PopoverMenu()
        self.popover.set_menu_model(self.menu)

        # Create a menu button
        self.hamburger = Gtk.MenuButton()
        self.hamburger.set_popover(self.popover)
        self.hamburger.set_icon_name("open-menu-symbolic")

        # Add menu button to the header bar
        self.header.pack_start(self.hamburger)
        self._add_about()

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
        self.menu.append("About", "win.about")

    def _add_slider(self):
        pass
        # self.slider_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        # self.content.append(self.slider_box)

        # self.slider = Gtk.Scale()
        # self.slider.set_digits(0)
        # self.slider.set_range(0, 10)
        # self.slider.set_draw_value(True)
        # self.slider.set_value(5)

        # self.slider.connect("value-changed", self.slider_changed)
        # self.slider_box.append(self.slider)

    def add_motor_controls(self):
        self.motor_controls = Adw.PreferencesGroup(
            title="Motor Controls",
            description="Controls for the mirror motor",
        )
        self.content.set_content(self.motor_controls)

        self.motor_position = Gtk.Scale(
            draw_value=True,
            adjustment=Gtk.Adjustment(
                lower=MOTOR_MIN_POS,
                upper=MOTOR_MAX_POS,
                step_increment=0.001,
                page_increment=1.0,
            ),
            digits=MOTOR_PRECISION,
            orientation=Gtk.Orientation.HORIZONTAL,
        )
        self.motor_position.set_format_value_func(
            lambda scale, value: f"{value:.{MOTOR_PRECISION}f} mm"
        )
        self.motor_controls.add(
            Adw.PreferencesRow(
                title="Mirror Position",
                child=self.motor_position,
            )
        )


class Application(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id=APP_ID,
        )
        self.connect("activate", self.on_activate)

    def on_activate(self, application):
        self.window = MainWindow(application=application)
        self.window.present()


###################
### Entry Point ###
###################

appplication = Application()
appplication.run(sys.argv)
