#!/usr/bin/env bash
set -euo pipefail
O=$PWD/out_skew
mkdir -p "$O"
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --binary --timing --x-initial unique -j 4 -Wno-fatal -Wno-WIDTH -DOT_MEM_NO_INIT --top-module tb_svc7_skew -Mdir "$O/obj" -o sim rtl/hdc/v41x/ot_s81svc7_skew_sram.sv tools/s81_dv/svc_rs/tb_svc7_skew.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v > "$O/build.log" 2>&1
for s in 1 29; do "$O/obj/sim" +verilator+rand+reset+2 +verilator+seed+$s > "$O/run_s$s.log" 2>&1;tail -n 5 "$O/run_s$s.log"; done
