#!/bin/bash
set -euo pipefail
mode=$1
out=$2
mkdir -p "$out"
mut=0
[ "$mode" = neg ] && mut=1
iverilog -g2012 -s tb_qkh_recip_leaf -Ptb_qkh_recip_leaf.MUT=$mut -o "$out/tb" rtl/test/nearhbm/tb_qkh_recip_leaf.sv rtl/hdc/nearhbm/ot_qkh_recip_leaf.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_sfu_p.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/lib/ot_rst_relay.sv
vvp "$out/tb"
