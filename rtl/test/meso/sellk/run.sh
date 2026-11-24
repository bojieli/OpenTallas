#!/bin/bash
# SELLK-1 ring bench: gold SELLK 0 vs cand SELLK 1, lock-step on every rclk edge, receiver phase sweep + mutant.
# usage: run.sh OUT
set -uo pipefail
R=$(cd "$(dirname "$0")/../../../.." && pwd)
OUT=${1:?output directory}; mkdir -p "$OUT"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
V=(verilator --binary --timing --build -j 8 --top-module tb_sellk -Wno-fatal)
SRC=("$R/rtl/test/meso/sellk/tb_sellk.sv" "$R/rtl/common/ot_dp_clk_landing_ca.sv" "$R/rtl/common/ot_meso_fifo.sv" "$R/rtl/common/ot_dp_clk_landing.sv")
"${V[@]}" --Mdir "$OUT/base" "${SRC[@]}" > "$OUT/build.log" 2>&1 || { echo BUILD_FAIL; tail -20 "$OUT/build.log"; exit 2; }
rc=0; : > "$OUT/lockstep.log"
PHASES="0 41 83 125 208 300 416 500 624 708 791"
for phase in $PHASES; do "$OUT/base/Vtb_sellk" +PHASE=$phase >> "$OUT/lockstep.log" 2>&1 || rc=1; done
for m in SELLK_POS; do
  "${V[@]}" -DOT_MESO_MUTANT_$m --Mdir "$OUT/m_$m" "${SRC[@]}" > "$OUT/build_$m.log" 2>&1 || { echo "MUTANT_BUILD_FAIL $m"; rc=1; continue; }
  : > "$OUT/mut_$m.log"
  for phase in $PHASES; do "$OUT/m_$m/Vtb_sellk" +PHASE=$phase >> "$OUT/mut_$m.log" 2>&1; done
  if grep -q SELLK_FAIL "$OUT/mut_$m.log"; then echo "MUTANT_CAUGHT $m $(grep -c SELLK_FAIL "$OUT/mut_$m.log")"; else echo "MUTANT_SURVIVED $m"; rc=1; fi
done
n=$(grep -c SELLK_PASS "$OUT/lockstep.log"); echo "PASS_PHASES $n / $(echo $PHASES | wc -w)"
[ "$n" = "$(echo $PHASES | wc -w)" ] || rc=1
echo "RC $rc"; exit $rc
