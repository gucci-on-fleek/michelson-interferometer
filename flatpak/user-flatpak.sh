#!/bin/sh
LD_LIBRARY_PATH=$HOME/.local/lib/ \
    PATH="/var/tmp/$USER/:$PATH" \
    XDG_DATA_DIRS="/home/$USER/.local/share/flatpak/exports/share:/var/lib/flatpak/exports/share" \
    exec $HOME/.local/libexec/flatpak --user "$@"
