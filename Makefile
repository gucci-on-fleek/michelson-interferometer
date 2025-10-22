# Michelson Interferometer Control Software
# https://github.com/gucci-on-fleek/michelson-interferometer
# SPDX-License-Identifier: MPL-2.0+
# SPDX-FileCopyrightText: 2025 Max Chernoff

# Target-style settings
.SUFFIXES:
MAKEFLAGS += --no-builtin-rules
.SILENT:
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
SHELL := /usr/bin/bash

# Variables
VENV := python3 -m venv

# Default target
.DEFAULT_GOAL := default
.PHONY: default
default:
	${error Please specify a target.}

# Create the venv and install dependencies
.PHONY: setup
setup: .venv/bin/activate ;

.venv/bin/activate: pyproject.toml
	${VENV} ./.venv
	pip3 install --upgrade pip
	source ./.venv/bin/activate
	pip3 install .
	touch ./.venv/bin/activate

# Build the GUI files
%.ui: %.blp
	blueprint-compiler compile $< --output $@

# Flatpak pip generator
flatpak/flatpak-pip-generator.py: setup
	wget 'https://raw.githubusercontent.com/flatpak/flatpak-builder-tools/main/pip/flatpak-pip-generator.py' -O $@
	chmod +x $@

flatpak/python3-modules.json: pyproject.toml flatpak/flatpak-pip-generator.py setup
	source ./.venv/bin/activate
	./flatpak/flatpak-pip-generator.py --output=$@ --pyproject-file=pyproject.toml --runtime=org.gnome.Platform//48

# Flatpak build
.PHONY: flatpak
flatpak: flatpak/ca.maxchernoff.michelson_interferometer.yaml michelson_interferometer/main.ui michelson_interferometer/*.py pyproject.toml
	flatpak-builder --user --install-deps-from=flathub --repo=repo --install builddir org.flatpak.Hello.yml

# Run the GUI
.PHONY: run
run: setup michelson_interferometer/main.ui michelson_interferometer/*.py
	source ./.venv/bin/activate
	python3 -m michelson_interferometer.gui
