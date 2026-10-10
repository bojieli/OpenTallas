#!/usr/bin/env bash
# hgi-adapters: D1 FUSED die body bench (tb_hgi_fused_unit).  usage: run_fused_unit.sh <outdir>
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "${1:-/tmp/hgi_fusedu_run}")
VL=${VERILATOR:-$( [ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && echo "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" || echo verilator)}
mkdir -p "$OUT"; cd "$ROOT"
python3 tools/hgi_adapters/fused_bench.py --out "$OUT/vec" > "$OUT/gen.log"
VEC="rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv
   rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
   rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv
   rtl/hdc/v41/ot_hdc_softplus.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_vec_lane.sv
   rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv rtl/hdc/v41x/ot_hdc_v41x_vec_red.sv rtl/hdc/v41x/ot_hdc_v41x_vec.sv"
SRC="rtl/hbm_accel/generic/adapters/ot_hgi_su_record.sv rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv
     rtl/hbm_accel/generic/adapters/ot_hgi_fused_record.sv rtl/hbm_accel/generic/peers/ot_hgi_dma_mover.sv
     rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv
     physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v $VEC"
"$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN \
  --top-module tb_hgi_fused_unit -I"$OUT/vec" -Mdir "$OUT/obj" $SRC rtl/hbm_accel/generic/adapters/tb/tb_hgi_fused_unit.sv \
  -j ${J:-16} > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log"; exit 2; }
"$OUT/obj/Vtb_hgi_fused_unit" +DIR="$OUT/vec" | tee "$OUT/run.log" | tail -12
