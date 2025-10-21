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

# Run the GUI
.PHONY: run
run: setup michelson_interferometer/main.ui michelson_interferometer/*.py
	source ./.venv/bin/activate
	python3 -m michelson_interferometer.gui
