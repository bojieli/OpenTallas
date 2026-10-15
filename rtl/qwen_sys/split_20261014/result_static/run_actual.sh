#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
root=../../..
iverilog -g2012 -s tb_actual -o actual.vvp "$root/hdc/ot_hdc_fastfp.sv" "$root/hdc/ot_hdc_prefix.sv" "$root/hdc/ot_hdc_fp32_add_lat.sv" "$root/hdc/ot_hdc_fp32_mul_lat.sv" "$root/hdc/nearhbm/ot_qwen_tp8_pv256_finalize_static.sv" qkd_result_static.sv qkd_result_finalize_collected.sv tb_actual.sv
vvp actual.vvp
sha256sum "$root/hdc/nearhbm/ot_qwen_tp8_pv256_finalize_static.sv" qkd_result_static.sv qkd_result_finalize_collected.sv tb_actual.sv
