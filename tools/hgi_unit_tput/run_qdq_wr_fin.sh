#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory}; mkdir -p "$out"
iverilog -g2012 -s tb_hgi_qdq_wr_fin -Ptb_hgi_qdq_wr_fin.MUT="${MUT:-0}" -o "$out/sim" rtl/lib/ot_rst_relay.sv rtl/hbm_accel/generic/qw/ot_hgi_qdq_wr_fin.sv rtl/test/hbm_accel/generic/tb_hgi_qdq_wr_fin.sv >"$out/build.log" 2>&1
vvp "$out/sim" >"$out/run.log" 2>&1
cat "$out/run.log"
