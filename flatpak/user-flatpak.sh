#!/bin/sh
LD_LIBRARY_PATH=$HOME/.local/lib/ PATH="/var/tmp/$USER/:$PATH" \
    exec $HOME/.local/libexec/flatpak --user "$@"
