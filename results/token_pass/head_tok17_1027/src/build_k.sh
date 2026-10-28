#!/bin/bash
# TOK-ALL-17: rebuild the TOK-16 rank-merge die bench with channel K=$1 (default 172)
K=$1
cd /srv/opentallas-scratch2/claude/wt/claude-tok17-head
exec /home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-PINMISSING --top-module tb -GK=$K -f /srv/opentallas-scratch2/claude/tok16-head-rm/die16.f --Mdir /srv/opentallas-scratch2/claude/tok17-head/obj_k$K --build-jobs 16 -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > /srv/opentallas-scratch2/claude/tok17-head/build_k$K.log 2>&1
