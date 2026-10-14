#!/bin/bash
set -euo pipefail
out=$(realpath -m "$1"); mut=${2:-0}
mkdir -p "$out"
iverilog -g2012 -s tb_no3_hub -Ptb_no3_hub.MUT="$mut" -o "$out/bench.vvp" physical/hbm_w2_rb_station_20261006/hub/ot_hbm_w2_stn_hub_no3.v physical/hbm_native_no3_pinaccess_1014/ot_hbm_native_no3_hub_m5_1014.sv physical/hbm_native_no3_pinaccess_1014/tb_no3_hub.sv
vvp -n "$out/bench.vvp" > "$out/simulation.log" 2>&1 || { cat "$out/simulation.log"; exit 1; }
cat "$out/simulation.log"
grep -q '^NO3_HUB_EXACT PASS' "$out/simulation.log"
