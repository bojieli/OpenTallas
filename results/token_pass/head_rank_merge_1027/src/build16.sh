#!/bin/bash
cd /srv/opentallas-scratch2/claude/wt/claude-tok16-head-1027
exec /home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-PINMISSING --top-module tb -f /srv/opentallas-scratch2/claude/tok16-head-rm/die16.f --Mdir /srv/opentallas-scratch2/claude/tok16-head-rm/obj16 --build-jobs 16 -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > /srv/opentallas-scratch2/claude/tok16-head-rm/build16.log 2>&1
