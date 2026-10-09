#!/usr/bin/env bash
set -euo pipefail
cd "${1:?source directory required}"
exec verilator --lint-only -Wno-fatal --top-module ot_qwen_r25_su_quarter \
  -GENABLE=1 -GN=256 -GM=64 -Irtl/test \
  rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv \
  rtl/hdc/ot_hdc_cg.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_ring.sv \
  rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv \
  rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv \
  rtl/hdc/ot_hdc_fastfp_lat_c12.sv rtl/hdc/ot_hdc_fp32_f12.sv \
  rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv \
  rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv \
  rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/v41x/ot_dsrom_su_f12.sv \
  rtl/hdc/v41/ot_hdc_fsqrt_c12.sv \
  rtl/hdc/v41x/ot_hdc_v41x_sfu_c12.sv rtl/hdc/v41x/ot_hdc_v41x_vec_lane_c12.sv \
  rtl/hdc/v41x/ot_hdc_v41x_vec_side_c12.sv rtl/hdc/v41x/ot_hdc_v41x_vec_red_c12.sv \
  rtl/hdc/v41x/ot_hdc_v41x_vec_c12.sv \
  rtl/qwen_r25_su_dispatch/ot_qwen_r25_su_quarter.sv
