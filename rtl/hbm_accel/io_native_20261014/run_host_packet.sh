#!/usr/bin/env bash
set -euo pipefail
out=$1; mut=${2:-0};mkdir -p "$out"
iverilog -g2012 -s tb_hbm_host_packet -Ptb_hbm_host_packet.MUT="$mut" -o "$out/sim" rtl/hbm_accel/io_native_20261014/{ot_hbm_host_packet,hfd_host_packet_face,tb_hbm_host_packet}.sv > "$out/build.log" 2>&1
vvp -n "$out/sim" > "$out/run.log" 2>&1
cat "$out/run.log"
grep -q '^HBM_HOST_PACKET_PASS' "$out/run.log"
