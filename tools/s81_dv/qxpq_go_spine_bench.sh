#!/bin/bash
set -euo pipefail
R=$(git rev-parse --show-toplevel)
B=${1:?scratch output directory required}
mkdir -p "$B"
V=${VERILATOR:-verilator}
git show df33c453ad:rtl/v41die/ot_v41_spine_pq_static_w17w10.sv | sed 's/module ot_v41_spine_pq_static_w17w10/module legacy_spine/' > "$B/legacy_spine.sv"
for flag in 1 0; do
 "$V" --binary --timing -Wno-fatal -Wno-lint -Wno-style +define+OT_PQ_ROM_PORTS +define+GB_FLAG=$flag --top-module tb_gb_spine --Mdir "$B/obj$flag" -j 4 -CFLAGS -O1 "$R/tools/s81_dv/tb_qxpq_go_spine.sv" "$B/legacy_spine.sv" "$R/rtl/v41die/ot_v41_spine_pq_static_w17w10.sv" "$R/rtl/hdc/ot_hdc_delay.sv" > "$B/build$flag.log" 2>&1
 if "$B/obj$flag/Vtb_gb_spine" > "$B/run$flag.log" 2>&1; then
  test "$flag" = 1
  grep -q 'GB_SPINE PASS gos3 ends3' "$B/run$flag.log"
 else
  test "$flag" = 0
  grep -q GO_DIFF "$B/run$flag.log"
 fi
done
echo GB_SPINE_GOLD_PASS_MUTANT_CAUGHT
