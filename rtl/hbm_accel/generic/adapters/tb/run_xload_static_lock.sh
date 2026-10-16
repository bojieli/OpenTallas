#!/usr/bin/env bash
# H-ELEM-A 2026-10-15: static SM x-load vs the production credited x-load (ot_hgi_sm_xload over ot_hgi_vm_unit).
# usage: run_xload_static_lock.sh <outdir> [MUT1|MUT2]   -> XLOAD_STATIC_LOCK PASS / FAIL
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd); OUT=$(realpath -m "$1"); MUT=${2:-}; mkdir -p "$OUT"; cd "$ROOT"
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
B="$OUT/obj${MUT:+_$MUT}"
verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style -j 8 ${MUT:+-D$MUT} --top-module tb_xload_static_lock --Mdir "$B" \
  rtl/lib/ot_rst_relay.sv rtl/hbm_accel/generic/peers/ot_hgi_sm_xload.sv rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static.sv \
  rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv rtl/link/ot_fifo_sram_fwft.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv \
  rtl/hbm_accel/generic/vm/ot_hgi_vm_wrd.sv rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_sfu.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v \
  rtl/hbm_accel/generic/adapters/tb/tb_hgi_xload_static_lock.sv > "$OUT/build${MUT:+_$MUT}.log" 2>&1 || { tail -30 "$OUT/build${MUT:+_$MUT}.log"; exit 1; }
"$B/Vtb_xload_static_lock" | tee "$OUT/slock${MUT:+_$MUT}.log" | grep -E "static first|ERR|cmd|PASS|FAIL" | tail -20
grep -q 'XLOAD_STATIC_LOCK PASS' "$OUT/slock${MUT:+_$MUT}.log"
