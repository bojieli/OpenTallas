#!/usr/bin/env bash
set -eu
out=$1
mut=${2:-0}
mkdir -p "$out"
iverilog -g2012 -s tb_static_run_target -Ptb_static_run_target.MUT="$mut" -o "$out/tb.vvp" \
 rtl/hbm_accel/host_static_20261015/ot_static_run_target.sv rtl/test/hbm_accel/svg_rel/tb_static_run_target.sv
vvp "$out/tb.vvp"
