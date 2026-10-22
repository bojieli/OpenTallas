#!/bin/bash
# QW-SU8 lockstep bench (fleet, Verilator 5.050): bench.sh OUT MUT(0|1|2) XI(0|1)
#   MUT 1 = wrong lane-3 stride offset, MUT 2 = program start accepted one alignment edge early; XI 1 = --x-initial unique
set -u
O=$1; M=${2:-0}; X=${3:-0}; mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version
XO="--x-assign 0 --x-initial 0"; RUNX=""
if [ "$X" = 1 ]; then XO="--x-assign unique --x-initial unique"; RUNX="+verilator+rand+reset+2 +verilator+seed+7"; fi
"$V" --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD $XO +define+SU8_MUT=$M +define+SU8_XI=$X \
  --top-module tb_su8 rtl/qwen_dv/s5/qfd_dv_s5_su8.sv rtl/qwen_dv/s5/qfd_dv_s5_su8_rst3.sv \
  rtl/test/qwen_dv/s5/su8/s7_kff.sv rtl/test/qwen_dv/s5/su8/su7_control_projection.sv rtl/test/qwen_dv/s5/su8/tb_su8.sv \
  -Mdir "$O/obj_${M}_$X" > "$O/build_${M}_$X.log" 2>&1 || { echo BUILD FAIL; tail -40 "$O/build_${M}_$X.log"; exit 1; }
"$O/obj_${M}_$X/Vtb_su8" $RUNX > "$O/run_${M}_$X.log" 2>&1
tail -12 "$O/run_${M}_$X.log"
grep -q 'SU8_EQ PASS' "$O/run_${M}_$X.log"
