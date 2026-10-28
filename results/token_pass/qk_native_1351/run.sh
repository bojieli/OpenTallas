#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
verilator --binary --timing -Wno-fatal --top-module tb -j 4 --Mdir obj tb.sv qkd_d2d_cal_seq_bc4_rom64.sv ot_qwen_d2d_cal_seq_rom64_core.sv ot_rom_64x32_m2.v > build.log 2>&1
for m in 0 1 2; do ./obj/Vtb +MUT=$m > sim_${m}.log 2>&1; cat sim_${m}.log; done
