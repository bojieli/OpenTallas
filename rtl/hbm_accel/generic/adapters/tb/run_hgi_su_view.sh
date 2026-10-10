#!/usr/bin/env bash
# hgi-1010/d: lockstep bench of the HGI unit-slot die view hfd_hgi_su (wrapper vs the same unit RTL driven directly;
# tools/hbm_die_wrap.py gen_tb).  usage: run_hgi_su_view.sh <outdir>
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "${1:-/tmp/hgi_su_view_run}")
VL=${VERILATOR:-$( [ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && echo "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" || echo verilator)}
mkdir -p "$OUT"; cd "$ROOT"
M=physical/asap7_memory_macros
SRC="rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv
  rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
  rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv
  rtl/hdc/v41/ot_hdc_softplus.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_vec_lane.sv
  rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv rtl/hdc/v41x/ot_hdc_v41x_vec_red.sv rtl/hdc/v41x/ot_hdc_v41x_vec.sv
  rtl/hdc/v41x/ot_hdc_v41x_hcp.sv rtl/hdc/hbm/ot_hdc_v41x_weight_window.sv rtl/hdc/v41/ot_hdc_sk_arith.sv
  rtl/hdc/v41/ot_hdc_sk_recip_rom.sv rtl/hdc/v41/ot_hdc_sinkhorn.sv rtl/hdc/v41/ot_hdc_sinkhorn_mc.sv
  rtl/hbm_accel/generic/adapters/ot_hgi_su_record.sv rtl/hbm_accel/generic/adapters/ot_hgi_sfu_record.sv
  rtl/hbm_accel/generic/adapters/ot_hgi_hc_record.sv rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv
  rtl/hbm_accel/generic/peers/ot_hgi_hc_unit.sv rtl/hbm_accel/generic/peers/ot_hgi_hbm_lane.sv
  $M/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v $M/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
  $M/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv
  rtl/common/ot_fwd_link_stage.sv physical/hbm_accel_die_views/hgi_su/rtl/hfd_hgi_su.sv"
"$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN \
  --top-module tb_hfd_hgi_su -Mdir "$OUT/obj" $SRC physical/hbm_accel_die_views/hgi_su/rtl/tb_hfd_hgi_su.sv -j ${J:-8} \
  > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log"; exit 2; }
"$OUT/obj/Vtb_hfd_hgi_su" | tee "$OUT/run.log" | tail -6
