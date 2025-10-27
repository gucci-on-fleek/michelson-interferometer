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
BLUEPRINT_COMPILER := blueprint-compiler

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

# Run the GUI
.PHONY: run-host
run-host: .venv/bin/activate michelson_interferometer/main.ui michelson_interferometer/*.py
	source ./.venv/bin/activate
	python3 -m michelson_interferometer.gui

# Make sure that Flathub is enabled
build/.flathub-enabled:
	flatpak --user remote-add --if-not-exists flathub \
		https://dl.flathub.org/repo/flathub.flatpakrepo
	touch $@

# Install the GNOME Flatpak SDK
build/.gnome-sdk-installed: build/.flathub-enabled
	flatpak --user install --assumeyes org.gnome.Sdk//49
	touch $@

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
	echo "modules:" >> ./flatpak/python-modules.yaml
	echo "  - name: python3" >> ./flatpak/python-modules.yaml
	echo "    buildsystem: simple" >> ./flatpak/python-modules.yaml
	echo "    build-commands:" >> ./flatpak/python-modules.yaml
	echo "      - pip3 install --prefix=/app --no-deps *" >> ./flatpak/python-modules.yaml
	echo "    sources:" >> ./flatpak/python-modules.yaml

	for file in ./build/wheels/* ; do
		name="$$(basename $$file)"
		url="$$(grep --fixed-strings "$$name$$$$" ./build/python-dependencies-urls.txt)"

		echo "      - type: file" >> ./flatpak/python-modules.yaml
		echo "        url: $$url" >> ./flatpak/python-modules.yaml
		echo "        sha256: $$(sha256sum $$file | cut -d' ' -f1)" >> ./flatpak/python-modules.yaml
		echo "" >> ./flatpak/python-modules.yaml
	done

# Build the Flatpak repository
build/repo/refs/heads/app/ca.maxchernoff.michelson_interferometer/x86_64/master: \
	build/.flathub-enabled \
	flatpak/ca.maxchernoff.michelson_interferometer.yaml \
	# (end of prerequisites)

	# Build the Flatpak
	flatpak-builder --user \
		--install-deps-from=flathub \
		--repo=./build/repo/ \
		--state-dir=./build/state/ \
		--force-clean \
		--install \
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

# Download the necessary Ubuntu packages
build/ubuntu-packages/.all-downloaded:
	mkdir -p build/ubuntu-packages/
	wget --directory-prefix build/ubuntu-packages/ \
		"http://security.ubuntu.com/ubuntu/pool/universe/f/flatpak/flatpak_1.12.7-1ubuntu0.1_amd64.deb" \
		"http://ubuntu.cs.utah.edu/ubuntu/pool/main/x/xdg-dbus-proxy/xdg-dbus-proxy_0.1.6-1_amd64.deb" \
		"http://ubuntu.cs.utah.edu/ubuntu/pool/universe/a/appstream-glib/libappstream-glib8_0.7.18-2_amd64.deb" \
		"http://ubuntu.cs.utah.edu/ubuntu/pool/universe/m/malcontent/libmalcontent-0-0_0.10.4-1_amd64.deb" \
		"http://ubuntu.cs.utah.edu/ubuntu/pool/universe/o/ostree/libostree-1-1_2022.2-3_amd64.deb"

	touch $@

# Unpack the Ubuntu packages
build/ubuntu-tree/.all-unpacked: build/ubuntu-packages/.all-downloaded
	mkdir -p ./build/ubuntu-tree/
	cd ./build/ubuntu-tree/

	for package in ../ubuntu-packages/*.deb; do
		ar x $$package
		tar xf ./data.tar.*
		rm ./*.tar.* ./debian-binary
	done

	touch ./.all-unpacked

# Creates the non-root Flatpak command installation bundle
.PHONY: build-flatpak-cmd-bundle
build-flatpak-cmd-bundle: build/flatpak.tar.zstd ;

build/flatpak.tar.zstd: flatpak/user-flatpak.sh
	rm -r ./build/flatpak-tree/ >/dev/null || true
	mkdir -p ./build/flatpak-tree/{lib,bin,libexec}/

	cp ./build/ubuntu-tree/usr/lib/x86_64-linux-gnu/* ./build/flatpak-tree/lib/
	cp ./build/ubuntu-tree/usr/bin/xdg-dbus-proxy ./build/flatpak-tree/bin/
	cp ./flatpak/user-flatpak.sh ./build/flatpak-tree/bin/flatpak
	cp ./build/ubuntu-tree/usr/bin/flatpak ./build/flatpak-tree/libexec/

	tar --zstd -cf ./build/flatpak.tar.zstd -C ./build/flatpak-tree/ .
