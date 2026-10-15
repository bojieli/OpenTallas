#!/usr/bin/env bash
set -euo pipefail
root=${HCOLL_ROOT:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel)}
out=$(realpath -m "$1");mkdir -p "$out";cd "$root"
p=rtl/hbm_accel/io_static_20261015
for m in 0 1 2;do
 iverilog -g2012 -s tb_stepped_frame_bits -Ptb_stepped_frame_bits.MUT="$m" -o "$out/m$m.sim" "$p/ot_hbm_static_gearbox_step.sv" "$p/ot_hbm_static_frame_transport_step.sv" "$p/tb_stepped_frame_bits.sv"
 vvp "$out/m$m.sim" > "$out/m$m.log" 2>&1
 rm "$out/m$m.sim"
 cat "$out/m$m.log"
done
