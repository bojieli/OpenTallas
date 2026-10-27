#!/bin/bash
set -eu
E=/srv/opentallas-scratch2/claude/codex-xh-consumer-1027
V=$HOME/.local/opentallas-tools/verilator-5.050/share/verilator/include
cd "$E"
g++ -O0 -Iobj -I"$V" -I"$V/vltstd" -c main_pins.cpp -o main_pins.o
g++ main_pins.o obj/Vtb__ALL.a obj/verilated.o obj/verilated_threads.o -pthread -latomic -o obj/Vtb_pins
