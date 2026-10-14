#!/bin/bash
set -eu
cd "$(dirname "$0")/../../.."
out=$(realpath -m "$1");mkdir -p "$out"
iverilog -g2012 -s tb_hcoll_reduce_lane8 -Ptb_hcoll_reduce_lane8.MUT="${2:-0}" -o "$out/sim" rtl/hbm_accel/tu/tb_hcoll_reduce_lane8.sv rtl/hbm_accel/tu/ot_hcoll_reduce_lane8.sv rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv
vvp "$out/sim"
