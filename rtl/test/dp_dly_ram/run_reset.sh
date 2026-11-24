#!/usr/bin/env bash
# DLYRAM-RESET reset-release bench.  usage: run_reset.sh REPO OUTDIR
# 4-state (iverilog, SRAM words X: OT_MEM_NO_INIT) and 2-state random power-up (verilator --x-initial unique, 8 seeds).
set -uo pipefail
R=$1; O=$2; mkdir -p "$O"; H=$(cd "$(dirname "$0")" && pwd)
M="$R/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
V=${OT_VERILATOR:-verilator}
vl() { if command -v "$V" >/dev/null; then "$V" "$@"; else docker run --rm -u $(id -u):$(id -g) -e CCACHE_DISABLE=1 -e HOME=/tmp -v /srv:/srv -w "$PWD" verilator/verilator:v5.032 "$@"; fi; }
S="$R/tools/die_plan/ot_dp_dly_ram.sv $M $H/tb_dp_dly_ram_reset.sv"
iverilog -g2012 -DOT_MEM_NO_INIT -DOT_DLY_RAM_PTR_INIT -s tb_dp_dly_ram_reset -o "$O/i4" $S || exit 2
iverilog -g2012 -DOT_MEM_NO_INIT -s tb_dp_dly_ram_reset -o "$O/i4n" $S || exit 2
echo "== 4-state, PTR_INIT, hold D+2 (must PASS)"; vvp -n "$O/i4" +HOFF=2 | grep "DLYRST hoff"
echo "== 4-state, PTR_INIT, hold D-5 (negative control, must FAIL)"; vvp -n "$O/i4" +HOFF=-5 | grep "DLYRST hoff"
echo "== 4-state, no PTR_INIT, hold D+2 (X pessimism, expected FAIL x>0)"; vvp -n "$O/i4n" +HOFF=2 | grep "DLYRST hoff"
vl --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style --x-assign unique --x-initial unique -DOT_MEM_NO_INIT \
  --top-module tb_dp_dly_ram_reset $S -Mdir "$O/v2" -o tb > "$O/verilate.log" 2>&1 || { tail -20 "$O/verilate.log"; exit 2; }
for s in 1 2 3 4 5 6 7 8; do
  echo "== 2-state random power-up seed $s: hold D+2 / D-5"
  "$O/v2/tb" +verilator+seed+$s +verilator+rand+reset+2 +HOFF=2 | grep "DLYRST hoff"
  "$O/v2/tb" +verilator+seed+$s +verilator+rand+reset+2 +HOFF=-5 | grep "DLYRST hoff"
done
