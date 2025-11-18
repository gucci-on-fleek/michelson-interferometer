<!-- Michelson Interferometer Control Software
     https://github.com/gucci-on-fleek/michelson-interferometer
     SPDX-License-Identifier: MPL-2.0+
     SPDX-FileCopyrightText: 2025 Max Chernoff
-->

Michelson Interferometer Control Software
=========================================

This repository contains a Python/GTK-based GUI used to control the
Michelson Interferometer used in the University of Calgary Senior
Physics Lab.

Installation
------------

1. Install Flatpak. If at all possible, please install this as root by
   running

   ```console
   $ sudo apt install flatpak
   ```

   If you cannot install Flatpak as root, it is possible to install it
   as an unprivileged user, but this is _very_ difficult and is best
   avoided.

2. Download the latest Flatpak bundle, either manually from the
   [releases
   page](https://github.com/gucci-on-fleek/michelson-interferometer/releases),
   or by running

   ```console
   $ cd ~/Downloads/
   $ wget https://github.com/gucci-on-fleek/michelson-interferometer/releases/latest/download/ca.maxchernoff.michelson_interferometer.flatpak
   ```

3. (Optional) OSTree is insanely slow over NFS, so if you're installing
   this as an unprivileged user, you should link your Flatpak
   installation folder to a local directory:

   ```console
   $ mkdir -p /var/tmp/$USER/flatpak
   $ ln -s /var/tmp/$USER/flatpak ~/.local/share/flatpak
   ```

4. Install the Flatpak bundle by running

   ```console
   $ flatpak install --user ~/Downloads/ca.maxchernoff.michelson_interferometer.flatpak
   ```

Usage
-----

If you launch the Flatpak without any arguments, it will open the GUI;
otherwise, it will forward any arguments to the Python interpreter.
Also, if you run the Flatpak from the root of this Git repository, it
will use the source code in that directory; otherwise, it will use the
bundled code.

So, if you just want to run the GUI included in the Flatpak, run

```console
$ flatpak run ca.maxchernoff.michelson_interferometer
```

Or if you want to run a modified version, run

```console
$ git clone https://github.com/gucci-on-fleek/michelson-interferometer.git
$ cd michelson-interferometer/
[make your changes]
$ make run-flatpak  # Using the Makefile properly rebuilds all the necessary files
```

Or if you want to open a Python REPL with the Flatpak's Python
interpreter (and all its included packages), run

```console
$ flatpak run ca.maxchernoff.michelson_interferometer -
```

For local development, you can set the `MI_FAKE_DEVICES` environment
variable to use random data instead of real hardware devices:

```console
$ MI_FAKE_DEVICES=1 make run-flatpak
```
