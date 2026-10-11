#!/usr/bin/env bash
# hgi-1010/b-hc: standalone ot_hgi_hc_eng bench (tb_hgi_hc_eng).  usage: run_hc_eng.sh <outdir>
#   env: XDEF (e.g. "-DHMUT=1 -DLQV=32"), TAG (obj/log suffix), PLUS (sim plusargs, e.g. +GDLY=400), J
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd)
OUT=$(realpath -m "${1:-/tmp/hgi_hc_eng_run}")
VL=${VERILATOR:-$( [ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && echo "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" || echo verilator)}
mkdir -p "$OUT"; cd "$ROOT"
[ -f "$OUT/vec/hc_sizes.svh" ] || python3 tools/hgi_adapters/hc_eng_bench.py --out "$OUT/vec" > "$OUT/gen.log"
SRC="rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv
   rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
   rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/v41x/ot_hdc_v41x_vec_red.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41/ot_hdc_fsqrt.sv
   rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/v41x/ot_dsrom_aq12.sv rtl/hdc/v41x/ot_dsrom_divc.sv
   rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/v41x/ot_dsrom_su_norm.sv rtl/hdc/v41x/ot_dsrom_su_hcpost.sv
   rtl/hbm_accel/generic/peers/ot_hgi_hc_eng.sv
   rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv rtl/link/ot_fifo_sram_fwft.sv
   physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
   physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
   physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
   physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
"$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-LATCH \
  ${XDEF:-} --top-module tb_hgi_hc_eng -I"$OUT/vec" -Mdir "$OUT/obj${TAG:-}" $SRC rtl/hbm_accel/generic/peers/tb_hgi_hc_eng.sv \
  -j ${J:-16} > "$OUT/build${TAG:-}.log" 2>&1 || { tail -30 "$OUT/build${TAG:-}.log"; exit 2; }
"$OUT/obj${TAG:-}/Vtb_hgi_hc_eng" +DIR="$OUT/vec" ${PLUS:-} | tee "$OUT/run${TAG:-}.log" | tail -12
