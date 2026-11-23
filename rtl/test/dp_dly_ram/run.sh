#!/usr/bin/env bash
# usage: run.sh REPO OUTDIR [SEED]
set -euo pipefail
R=$1; O=$2; S=${3:-1}
V=${OT_VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$O"
H=$(dirname "$0")
"$V" --binary --timing -O2 --x-assign unique --x-initial unique -Wall -Wno-fatal -Wno-DECLFILENAME -Wno-MULTITOP \
  --top-module tb_dp_dly_ram "$R/tools/die_plan/ot_dp_dly_ram.sv" \
  "$R/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v" "$H/tb_dp_dly_ram.sv" \
  -Mdir "$O" -o tb > "$O/verilate.log" 2>&1 || { tail -30 "$O/verilate.log"; exit 2; }
grep -E "%Warning-(WIDTH|UNUSED|UNDRIVEN|LATCH|MULTIDRIVEN)" "$O/verilate.log" | grep "ot_dp_dly_ram.sv" || true
"$O/tb" +verilator+seed+$S +verilator+rand+reset+2
