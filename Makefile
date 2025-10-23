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
	$(error Please specify a target.)

# Build the GUI files
%.ui: %.blp
	blueprint-compiler compile $< --output=$@

# Create the venv and install dependencies
.PHONY: _setup-venv
_setup-venv: .venv/bin/activate

.venv/bin/activate: pyproject.toml
	# Create the virtual environment and activate it
	${VENV} ./.venv/
	source ./.venv/bin/activate

	# Upgrade pip inside the venv so that it recognizes pyproject.toml
	pip3 install --upgrade pip

	# Install the packages
	pip3 install .[dev, gtk]

	# Touch the activate file so that make knows the target is up to date
	touch ./.venv/bin/activate

# Run the GUI
.PHONY: host-run
run: _setup-venv michelson_interferometer/main.ui michelson_interferometer/*.py
	source ./.venv/bin/activate
	python3 -m michelson_interferometer.gui

# Make sure that Flathub is enabled
.PHONY: _flatpak-setup-flathub
_flatpak-setup: build/.flathub-enabled ;

flatpak/.flathub-enabled:
	flatpak --user remote-add --if-not-exists flathub \
		https://dl.flathub.org/repo/flathub.flatpakrepo

	touch $@

# Install the GNOME Flatpak SDK
.PHONY: _flatpak-setup-sdk
_flatpak-setup: build/.gnome-sdk-installed ;

build/.gnome-sdk-installed: _flatpak-setup-flathub
	flatpak --user install --assumeyes org.gnome.Sdk//48

	touch $@

# Download the Python dependencies for the Flatpak build
.PHONY: _download-flatpak-deps
_download-flatpak-deps: build/wheels/.all-downloaded ;

build/wheels/.all-downloaded: _flatpak-setup-sdk pyproject.toml
	# Download all the dependencies
	flatpak --user run \
		--devel \
		--share=network \
		--filesystem=host \
		--command=pip3 \
		org.gnome.Sdk//48 \
		download \
			--only-binary=":all:" \
			--no-binary="pyft232" \
			--no-build-isolation \
			--dest=./build/wheels/ \
			"."

# Build the Flatpak repository
.PHONY: _build-flatpak-repo
_build-flatpak-repo: build/repo/refs/heads/app/ca.maxchernoff.michelson_interferometer/x86_64/master ;

build/repo/refs/heads/app/ca.maxchernoff.michelson_interferometer/x86_64/master:
	_flatpak-setup-flathub \
	_download-flatpak-deps \
	flatpak/ca.maxchernoff.michelson_interferometer.yaml \
	# (end of prerequisites)

	# Build the Flatpak
	flatpak-builder --user \
		--install-deps-from=flathub \
		--repo=./build/flatpak/ \
		--state-dir=./build/state/ \
		--force-clean \
		--install \
		./build/flatpak/
		./flatpak/ca.maxchernoff.michelson_interferometer.yaml

# Bundle the Flatpak into a single file
.PHONY: build-flatpak
build-flatpak: build/ca.maxchernoff.michelson_interferometer.flatpak ;

build/ca.maxchernoff.michelson_interferometer.flatpak: _build-flatpak-repo
	# Create the Flatpak bundle
	flatpak --user build-bundle \
		./build/repo/ \
		./build/ca.maxchernoff.michelson_interferometer.flatpak
		"ca.maxchernoff.michelson_interferometer"

