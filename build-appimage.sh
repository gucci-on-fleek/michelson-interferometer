#!/bin/sh
# Michelson Interferometer Control Software
# https://github.com/gucci-on-fleek/michelson-interferometer
# SPDX-License-Identifier: MPL-2.0+
# SPDX-FileCopyrightText: 2025 Max Chernoff
set -eu

# Install the necessary packages
apt update
apt install --no-install-recommends -y \
    binutils \
    fakeroot \
    gtk-update-icon-cache \
    libgdk-pixbuf2.0-bin \
    libglib2.0-bin \
    python3-gi \
    python3-gi-cairo \
    python3-pip \
    squashfs-tools

pip3 install --break-system-packages --root-user-action=ignore appimage-builder==1.1.0

# Build the AppImage
cd /srv/
appimage-builder --recipe /srv/AppImageBuilder.yml
