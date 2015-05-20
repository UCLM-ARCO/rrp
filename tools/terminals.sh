#!/bin/bash
# -*- mode: sh; coding: utf-8 -*-

TERM="gnome-terminal"

function show_tty() {
    local port=$1
    local position=$2

    local cmd="microcom -p $port -s 115200"
    local options=" --hide-menubar -e '$cmd' --geometry $position"

    eval $TERM $options
}


offset=$1
[[ -n "$offset" ]] || offset=0

show_tty /dev/ttyUSB0 80x15+$offset+0
show_tty /dev/ttyUSB1 80x15+$offset+330
show_tty /dev/ttyUSB2 80x15+$offset+660
