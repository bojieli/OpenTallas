#!/usr/bin/env bash
# hgi-1010/d: SM publication bench: ot_hgi_sm_pub (banked-SRAM form) vs the flop form, random MATVEC results from 32 SMs
# (VM images compared against the expected words).  usage: run_pub_lock.sh <outdir> [MUT_PAR|MUT_ROWM]
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd); OUT=$(realpath -m "$1"); MUT=${2:-}; mkdir -p "$OUT"; cd "$ROOT"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D="${XDEF:-}"; [ -n "$MUT" ] && D="$D -D$MUT"
"$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN $D --top-module tb_pub_lock \
  -Mdir "$OUT/obj${MUT:+_$MUT}" rtl/hbm_accel/generic/peers/ot_hgi_sm_pub.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv \
  rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
  rtl/hbm_accel/generic/adapters/tb/tb_hgi_pub_lock.sv -j ${J:-8} > "$OUT/build${MUT:+_$MUT}.log" 2>&1 || { tail -30 "$OUT/build${MUT:+_$MUT}.log"; exit 2; }
"$OUT/obj${MUT:+_$MUT}/Vtb_pub_lock" | tee "$OUT/run${MUT:+_$MUT}.log" | tail -12
