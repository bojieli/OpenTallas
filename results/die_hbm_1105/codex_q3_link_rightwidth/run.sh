#!/bin/bash
set -eu
cd "$(dirname "$0")"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
verilator --binary --timing --top-module tb -Wno-fatal -j 4 -Mdir obj tb.sv leaf_old.sv leaf_new.sv ot_sram_1r1w_64x512_m1_r2c2.v ot_sram_1r1w_64x141_m1_r0c0_g141.v >build.log 2>&1
./obj/Vtb >result.log 2>&1
cat result.log
