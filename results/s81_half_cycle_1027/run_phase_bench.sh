#!/bin/bash
set -euo pipefail
B=${1:?scratch output directory required}
mkdir -p "$B"
R=$(git rev-parse --show-toplevel)
cp "$R/results/s81_half_cycle_1027/tb.sv" "$B/tb.sv"
V=${VERILATOR:-verilator}
for m in 0 1;do
 "$V" --binary --timing -Wno-fatal -Wno-lint -Wno-style +define+MUT=$m --top-module tb_half_phase --Mdir "$B/obj$m" -j 2 "$B/tb.sv" > "$B/build$m.log" 2>&1
 if "$B/obj$m/Vtb_half_phase" > "$B/run$m.log" 2>&1;then test "$m" = 0;else test "$m" = 1;grep -q DIFF "$B/run$m.log";fi
done
echo HALF_PHASE_POSITIVE_PASS_MUTANT_CAUGHT
