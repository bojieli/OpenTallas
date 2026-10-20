#!/bin/bash
set -eu
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
mkdir -p cap
/usr/bin/time -v -o cap/build.time "$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -DOT_MEM_NO_INIT --top-module tb_s81sl_cap_phase -Mdir cap/obj -f source_files.f --build-jobs 4 -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' >cap/build.log 2>&1
/usr/bin/time -v -o cap/run.time cap/obj/Vtb_s81sl_cap_phase +DIR=model >cap/run.log 2>&1
cap/obj/Vtb_s81sl_cap_phase +DIR=model +MODE=1 >cap/original_tree_negative.log 2>&1
