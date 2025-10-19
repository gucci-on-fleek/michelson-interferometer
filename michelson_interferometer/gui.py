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


#########################
### Class Definitions ###
#########################


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._setup_window()
        self._add_menu_bar()

        self.content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_child(self.content)

        self._add_slider()

    def _setup_window(self):
        self.set_default_size(600, 250)
        self.set_title("Michelson Interferometer")
        GLib.set_application_name("Michelson Interferometer")

    def _add_menu_bar(self):
        # Create a new menu, containing that action
        menu = Gio.Menu.new()

        self.header = Gtk.HeaderBar()
        self.set_titlebar(self.header)

        # Create a popover
        self.popover = Gtk.PopoverMenu()
        self.popover.set_menu_model(menu)

        # Create a menu button
        self.hamburger = Gtk.MenuButton()
        self.hamburger.set_popover(self.popover)
        self.hamburger.set_icon_name("open-menu-symbolic")

        # Add menu button to the header bar
        self.header.pack_start(self.hamburger)

        # Create an action to run a *show about dialog* function we will create
        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.show_about)
        self.add_action(action)

        menu.append("About", "win.about")

    def show_about(self, action, param):
        self.about = Gtk.AboutDialog()
        self.about.set_transient_for(self)
        self.about.set_modal(True)

        self.about.set_authors(["Max Chernoff"])
        self.about.set_license_type(Gtk.License.MPL_2_0)
        self.about.set_website(
            "https://github.com/gucci-on-fleek/michelson-interferometer"
        )
        self.about.set_website_label("GitHub Repository")
        self.about.set_version("0.0")

        self.about.set_visible(True)

    def _add_slider(self):
        self.slider_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.content.append(self.slider_box)

        self.slider = Gtk.Scale()
        self.slider.set_digits(0)
        self.slider.set_range(0, 10)
        self.slider.set_draw_value(True)
        self.slider.set_value(5)

        self.slider.connect("value-changed", self.slider_changed)
        self.slider_box.append(self.slider)

    def slider_changed(self, slider):
        print(int(slider.get_value()))


class Application(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="ca.maxchernoff.michelson_interferometer"
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
