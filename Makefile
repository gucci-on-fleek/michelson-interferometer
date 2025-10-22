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
setup: .venv/bin/activate
	flatpak --user install org.gnome.Sdk//48

.venv/bin/activate: pyproject.toml
	${VENV} ./.venv
	pip3 install --upgrade pip
	source ./.venv/bin/activate
	pip3 install .[dev,gtk]
	touch ./.venv/bin/activate

# Build the GUI files
%.ui: %.blp
	blueprint-compiler compile $< --output $@

# Flatpak pip generator
flatpak/flatpak-pip-generator.py: setup
	wget 'https://github.com/flatpak/flatpak-builder-tools/raw/refs/heads/master/pip/flatpak-pip-generator.py' -O $@
	chmod +x $@

# Flatpak build
.PHONY: flatpak
flatpak: ca.maxchernoff.michelson_interferometer.flatpak ;

ca.maxchernoff.michelson_interferometer.flatpak: flatpak/ca.maxchernoff.michelson_interferometer.yaml michelson_interferometer/main.ui michelson_interferometer/*.py pyproject.toml
	source ./.venv/bin/activate
	flatpak --user run --devel --share=network --filesystem=host --command=pip3 org.gnome.Sdk//48 download --only-binary=":all:" --no-binary="pyft232" --no-build-isolation --dest=./wheels/ .
	flatpak remote-add --if-not-exists --user flathub https://dl.flathub.org/repo/flathub.flatpakrepo
	flatpak-builder --user --install-deps-from=flathub --repo=repo --install --ccache --force-clean ./build/ $<
	flatpak build-bundle ./repo ca.maxchernoff.michelson_interferometer.flatpak ca.maxchernoff.michelson_interferometer

# Run the GUI
.PHONY: run
run: setup michelson_interferometer/main.ui michelson_interferometer/*.py
	source ./.venv/bin/activate
	python3 -m michelson_interferometer.gui
