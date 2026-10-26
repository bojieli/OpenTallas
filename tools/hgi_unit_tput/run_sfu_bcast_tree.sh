#!/usr/bin/env bash
# Cycle equivalence of the registered SFU broadcast tree (4 nodes + 16 e123 mappers) vs 16 monolithic lane mappers.
set -euo pipefail
out=$(realpath -m "$1"); mkdir -p "$out"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$vl" --binary --timing -O2 -j 4 -Wno-fatal -Wno-lint -GMUT="${MUT:-0}" --top-module tb_hgi_sfu_bcast_tree -Mdir "$out/obj" -o sim \
 rtl/hdc/ot_hdc_delay_ring.sv rtl/hbm_accel/generic/peers/ot_hgi_sfu_lane_map.sv rtl/hbm_accel/generic/peers/ot_hgi_sfu_bcast_tree.sv \
 rtl/test/hbm_accel/generic/tb_hgi_sfu_bcast_tree.sv > "$out/build.log" 2>&1
set +e
"$out/obj/sim" > "$out/run.log" 2>&1
rc=$?
set -e
cat "$out/run.log"
grep -q "PASS SFU_BCAST_TREE" "$out/run.log" || exit 1
exit $rc
