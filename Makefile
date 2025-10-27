# Michelson Interferometer Control Software
# https://github.com/gucci-on-fleek/michelson-interferometer
# SPDX-License-Identifier: MPL-2.0+
# SPDX-FileCopyrightText: 2025 Max Chernoff

################
### Settings ###
################

# Remove the builtin rules
.SUFFIXES:
MAKEFLAGS += --no-builtin-rules

# Silence the commands
.SILENT:

# Shell settings
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
SHELL := /usr/bin/bash

# By default, use the "venv" module, but allow overriding for the PJL computers
# that require you to use the "virtualenv" command.
VENV := python3 -m venv

# Use the host's blueprint-compiler by default, but allow overriding so that
# you can use a copy inside of the Flatpak.
BLUEPRINT_COMPILER := blueprint-compiler

# You'll want to modify this unless you're me :)
GPG_OPTS := --gpg-sign=5C696408F561E6C2A12A2BA08FD44004DB2B757E


####################
### Host Targets ###
####################

# Default target
.DEFAULT_GOAL := default
.PHONY: default
default:
	$(error Please specify a target.)

# Build the GUI files
%.ui: %.blp
	${BLUEPRINT_COMPILER} compile $< --output=$@

# Create the venv and install dependencies
.venv/bin/activate: pyproject.toml
	# Create the virtual environment and activate it
	${VENV} ./.venv/ || true
	source ./.venv/bin/activate

	# Upgrade pip inside the venv so that it recognizes pyproject.toml
	pip3 install --upgrade pip

	# Install the packages
	pip3 install .[dev]

	# Touch the activate file so that make knows the target is up to date
	touch ./.venv/bin/activate

# Run the GUI on the host
.PHONY: run-host
run-host: .venv/bin/activate michelson_interferometer/main.ui michelson_interferometer/*.py
	source ./.venv/bin/activate
	python3 -m michelson_interferometer.gui

.PHONY: update-version
update-version:
	git ls-files | xargs sed -Ei \
		-e "/%%[v]ersion/ s/[[:digit:]]\.[[:digit:]]\.[[:digit:]]/${version}/" \
		-e "/%%[d]ashdate/ s/[[:digit:]]{4}.[[:digit:]]{2}.[[:digit:]]{2}/$$(date -I)/" \
		-e "/%%[s]lashdate/ s|[[:digit:]]{4}.[[:digit:]]{2}.[[:digit:]]{2}|$$(date +%Y/%m/%d)|" \

#######################
### Flatpak Targets ###
#######################

# Make sure that Flathub is enabled
build/.flathub-enabled:
	flatpak --user remote-add --if-not-exists flathub \
		https://dl.flathub.org/repo/flathub.flatpakrepo

	mkdir ./build/ && touch $@

# Install the GNOME Flatpak SDK
build/.gnome-sdk-installed: build/.flathub-enabled
	flatpak --user install --assumeyes org.gnome.Sdk//49
	mkdir ./build/ && touch $@

# Download the Python dependencies for the Flatpak build
flatpak/python-modules.yaml: build/.gnome-sdk-installed pyproject.toml
	# Clear the previous downloads
	rm -r ./build/wheels/ >/dev/null || true
	mkdir -p ./build/wheels/
	truncate --size=0 ./flatpak/python-modules.yaml

	# Download all the dependencies
	flatpak --user run \
		--devel \
		--share=network \
		--filesystem=host \
		--command=pip3 \
		org.gnome.Sdk//49 \
		download \
			--only-binary=":all:" \
			--no-binary="pyft232" \
			--no-build-isolation \
			--dest=./build/wheels/ \
			--no-cache-dir \
			--verbose --verbose \
			"." \
		| grep \
			--only-matching \
			--perl-regexp \
			'(?<=https://files\.pythonhosted\.org:443 "GET )/packages/\S+' \
		| grep --invert-match 'metadata' \
		| sed 's|^|https://files.pythonhosted.org|' \
		> ./build/python-dependencies-urls.txt

	# Create the Flatpak module file
	echo "name: python-dependencies" >> ./flatpak/python-modules.yaml
	echo "modules:" >> ./flatpak/python-modules.yaml
	echo "  - name: python-dependencies" >> ./flatpak/python-modules.yaml
	echo "    buildsystem: simple" >> ./flatpak/python-modules.yaml
	echo "    build-commands:" >> ./flatpak/python-modules.yaml
	echo "      - pip3 install --prefix=/app --exists-action=ignore --no-deps *" >> ./flatpak/python-modules.yaml
	echo "    sources:" >> ./flatpak/python-modules.yaml

	for file in ./build/wheels/* ; do
		name="$$(basename $$file)"
		url="$$(grep --fixed-strings "$$name" ./build/python-dependencies-urls.txt)"

		echo "      - type: file" >> ./flatpak/python-modules.yaml
		echo "        url: $$url" >> ./flatpak/python-modules.yaml
		echo "        sha256: $$(sha256sum $$file | cut -d' ' -f1)" >> ./flatpak/python-modules.yaml
		echo "" >> ./flatpak/python-modules.yaml
	done

# Build the Flatpak repository
build/repo/refs/heads/app/ca.maxchernoff.michelson_interferometer/x86_64/master: \
	build/.flathub-enabled \
	flatpak/ca.maxchernoff.michelson_interferometer.yaml \
	flatpak/python-modules.yaml \
	michelson_interferometer/*.py \
	michelson_interferometer/main.ui \
	# (end of prerequisites)

	# Build the Flatpak
	flatpak-builder --user \
		--install-deps-from=flathub \
		--repo=./build/repo/ \
		--state-dir=./build/state/ \
		--keep-build-dirs \
		--force-clean \
		--install \
		${GPG_OPTS} \
		./build/flatpak/ \
		./flatpak/ca.maxchernoff.michelson_interferometer.yaml

# Bundle the Flatpak into a single file
.PHONY: build-flatpak
build-flatpak: build/ca.maxchernoff.michelson_interferometer.flatpak ;

build/ca.maxchernoff.michelson_interferometer.flatpak: \
	build/repo/refs/heads/app/ca.maxchernoff.michelson_interferometer/x86_64/master
	# (end of prerequisites)

	# Create the Flatpak bundle
	flatpak build-bundle \
		./build/repo/ \
		./build/ca.maxchernoff.michelson_interferometer.flatpak \
		"ca.maxchernoff.michelson_interferometer"

# Run the Flatpak
.PHONY: run-flatpak
run-flatpak:
	make BLUEPRINT_COMPILER="flatpak run \
		--command=blueprint-compiler ca.maxchernoff.michelson_interferometer" \
		michelson_interferometer/main.ui

	flatpak run ca.maxchernoff.michelson_interferometer \
		-m michelson_interferometer.gui
