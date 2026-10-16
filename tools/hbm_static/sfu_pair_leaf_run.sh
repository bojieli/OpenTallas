#!/bin/bash
set -euo pipefail
out=$1; shift
mkdir -p "$out"
iverilog -g2012 -s tb_hgi_sfu_lg_pair_leaf -o "$out/leaf.vvp" rtl/hdc/ot_hdc_delay.sv rtl/hbm_accel/generic/peers/ot_hgi_sfu_lg_pair_leaf.sv rtl/test/hbm_accel/generic/tb_hgi_sfu_lg_pair_leaf.sv
vvp "$out/leaf.vvp" "$@"
