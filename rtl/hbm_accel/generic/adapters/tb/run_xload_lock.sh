#!/usr/bin/env bash
# FILL-9 (2026-10-10): SRAM-macro SM x-load vs the flop-banked reference, 10 random commands, every x-store write
# identical.  usage: run_xload_lock.sh <outdir> [MUT_T|MUT_M]   -> prints XLOAD_LOCK PASS / FAIL
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd); OUT=$(realpath -m "$1"); MUT=${2:-}; mkdir -p "$OUT"; cd "$ROOT"
iverilog -g2012 ${MUT:+-D$MUT} -s tb_xload_lock -o "$OUT/lock${MUT:+_$MUT}.vvp" \
  rtl/lib/ot_rst_relay.sv rtl/hbm_accel/generic/peers/ot_hgi_sm_xload.sv rtl/hbm_accel/generic/adapters/tb/ref/ot_hgi_sm_xload_old.sv \
  rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
  rtl/hbm_accel/generic/adapters/tb/tb_hgi_xload_lock.sv
vvp "$OUT/lock${MUT:+_$MUT}.vvp" | tee "$OUT/lock${MUT:+_$MUT}.log" | tail -4
grep -q 'XLOAD_LOCK PASS' "$OUT/lock${MUT:+_$MUT}.log"
