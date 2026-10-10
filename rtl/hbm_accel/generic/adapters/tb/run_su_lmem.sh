#!/usr/bin/env bash
# hgi-1010/d: banked SU local memory bench (Verilator).  usage: run_su_lmem.sh <outdir> [MUT_XBAR]
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "${1:-/tmp/hgi_su_lmem_run}"); MUT=${2:-}
VL=${VERILATOR:-$( [ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && echo "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" || echo verilator)}
mkdir -p "$OUT"; cd "$ROOT"
M=physical/asap7_memory_macros
SRC="rtl/hbm_accel/generic/adapters/ot_hgi_su_record.sv rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv
     $M/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v $M/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
     $M/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
D=""; [ -n "$MUT" ] && D="-D$MUT"
"$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN $D \
  --top-module tb_hgi_su_lmem -Mdir "$OUT/obj${MUT:+_$MUT}" $SRC rtl/hbm_accel/generic/adapters/tb/tb_hgi_su_lmem.sv -j ${J:-8} \
  > "$OUT/build${MUT:+_$MUT}.log" 2>&1 || { tail -30 "$OUT/build${MUT:+_$MUT}.log"; exit 2; }
"$OUT/obj${MUT:+_$MUT}/Vtb_hgi_su_lmem" | tee "$OUT/run${MUT:+_$MUT}.log" | tail -6
