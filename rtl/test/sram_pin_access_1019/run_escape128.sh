#!/usr/bin/env bash
# QW-SRAM3 10-19: behaviour bench of the CTL128x64 escape coupon. usage: run_escape128.sh <outdir> [mut]
set -uo pipefail
OUT=${1:-.}; MUT=0; [ "${2:-}" = mut ] && MUT=1
mkdir -p "$OUT"
v=$(command -v verilator || true); for c in /opt/verilator-5.050/bin/verilator $HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; do [ -x $c ] && v=$c; done
"$v" --version
"$v" --binary --timing -Wno-fatal --top-module tb_escape128 -GMUT=$MUT --Mdir "$OUT/obj_$MUT" -o sim \
  rtl/test/sram_pin_access_1019/tb_escape128.sv rtl/test/sram_pin_access_1019/escape128_harness.sv \
  physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1/ot_sram_1r1w2c_128x64_m1.v > "$OUT/build_$MUT.log" 2>&1 || { tail -20 "$OUT/build_$MUT.log"; exit 3; }
"$OUT/obj_$MUT/sim"
