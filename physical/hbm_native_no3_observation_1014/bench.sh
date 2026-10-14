#!/bin/bash
set -euo pipefail
out=$(realpath -m "$1");mut=${2:-0};mkdir -p "$out"
cd "$(dirname "$0")/../.."
iverilog -g2012 -s tb_no3_composition -Ptb_no3_composition.MUT="$mut" -o "$out/sim.vvp" physical/hbm_native_no3_observation_1014/tb_composition.sv physical/hbm_native_no3_observation_1014/ot_hbm_native_no3_composition_1014.sv physical/hbm_native_no3_observation_1014/ot_hbm_native_no3_hub_observe_1014.sv physical/hbm_w2_rb_station_20261006/hub/ot_hbm_w2_stn_hub_no3.v physical/hbm_w2_rb_station_20261006/{slice_static,station_rb_static,bank_veto_static}.sv
vvp -n "$out/sim.vvp" > "$out/simulation.log" 2>&1 || { cat "$out/simulation.log";exit 1; }
cat "$out/simulation.log"
grep -q '^NO3_COMPOSITION PASS' "$out/simulation.log"
