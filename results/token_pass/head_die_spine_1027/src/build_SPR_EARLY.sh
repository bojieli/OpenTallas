#!/bin/bash
cd /srv/opentallas-scratch2/claude/wt/claude-tok15-1027
exec /home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-PINMISSING --top-module tb -f /srv/opentallas-scratch2/claude/tok15-head-die/die.f --Mdir /srv/opentallas-scratch2/claude/tok15-head-die/obj_SPR_EARLY +define+OT_S81HD_MUT_SPR_EARLY --build-jobs 16 -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > /srv/opentallas-scratch2/claude/tok15-head-die/build_SPR_EARLY.log 2>&1
