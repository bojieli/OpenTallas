#!/bin/bash
set -euo pipefail
V="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$V" --binary --timing -j 1 -O1 -Wno-fatal -Wno-WIDTH -Wno-UNOPTFLAT --top-module read_oh_tb -GTR=1 -DOT_S81DV_MUT_LEAF -Mdir "$PWD/obj" "$PWD/read_oh_helpers.sv" "$PWD/read_oh_tb.sv" -MAKEFLAGS "OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0" >build.log 2>&1
./obj/Vread_oh_tb >run.log 2>&1
cat run.log
grep -q 'bad=0' run.log
