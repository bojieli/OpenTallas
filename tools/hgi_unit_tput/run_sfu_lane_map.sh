#!/usr/bin/env bash
# Fixed-lane port equivalence against frozen ot_su12_sfu's lane_id dependencies.
set -euo pipefail
out=$(realpath -m "$1"); mkdir -p "$out"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
if [ ! -x "$vl" ]; then vl=verilator; fi
"$vl" --binary --timing -O2 -j 4 -Wno-fatal -Wno-lint -GMUT="${MUT:-0}" --top-module tb_hgi_sfu_lane_map -Mdir "$out/obj" -o sim \
 rtl/hdc/ot_hdc_delay_ring.sv rtl/hbm_accel/generic/peers/ot_hgi_sfu_lane_map.sv rtl/test/hbm_accel/generic/tb_hgi_sfu_lane_map.sv > "$out/build.log" 2>&1
"$out/obj/sim" > "$out/run.log" 2>&1
cat "$out/run.log"
