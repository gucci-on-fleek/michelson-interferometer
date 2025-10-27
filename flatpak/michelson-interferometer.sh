#!/bin/sh
# Michelson Interferometer Control Software
# https://github.com/gucci-on-fleek/michelson-interferometer
# SPDX-License-Identifier: MPL-2.0+
# SPDX-FileCopyrightText: 2025 Max Chernoff
set -eu

if [ "$#" -eq 0 ]; then
    exec python3 -m michelson_interferometer.gui
else
    exec python3 "$@"
fi
