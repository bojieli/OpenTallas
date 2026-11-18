#!/bin/bash
# RING-LITE-1 (KV-RING2-LIGHT 11-18): lock-step LITE 1 vs 0 (q identical every clk edge, 0 cycles; lite status as
# declared) over 11 receiver phases x 196 ring forms; negative controls (lite mutant reads one slot late; +SHIFT=1
# wrong declared latency) must FAIL; verilator lint LITE 0 vs 1.  usage: run.sh OUT
set -uo pipefail
R=$(cd "$(dirname "$0")/../../../.." && pwd)
OUT=${1:?output directory}; mkdir -p "$OUT"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
V=(verilator --binary --timing --build -j 8 --top-module tb_lite -Wno-fatal)
SRC=("$R/rtl/test/meso/lite/tb_lite.sv" "$R/rtl/common/ot_dp_clk_landing_ca.sv" "$R/rtl/common/ot_meso_fifo.sv" "$R/rtl/common/ot_dp_clk_landing.sv")
rc=0
for top in ot_dp_clk_landing_ca ot_dp_clk_landing_cas; do for lt in 0 1; do
  verilator --lint-only -Wall --top-module $top -GW=2 -GLITE=$lt "${SRC[@]:1}" > "$OUT/lint_${top}_$lt.log" 2>&1
  echo "LINT $top W=2 LITE=$lt warnings=$(grep -c '%Warning' "$OUT/lint_${top}_$lt.log") errors=$(grep -c '%Error' "$OUT/lint_${top}_$lt.log")"
done; done
"${V[@]}" --Mdir "$OUT/base" "${SRC[@]}" > "$OUT/build.log" 2>&1 || { echo BUILD_FAIL; tail -20 "$OUT/build.log"; exit 2; }
: > "$OUT/lockstep.log"
for phase in 0 41 83 125 208 400 416 433 624 791 830; do "$OUT/base/Vtb_lite" +PHASE=$phase >> "$OUT/lockstep.log" 2>&1 || rc=1; done
echo "PASS_RUNS $(grep -c LITE_PASS "$OUT/lockstep.log") of 11; MISMATCH_LINES $(grep -c LT_MISMATCH "$OUT/lockstep.log")"
grep LITE_PASS "$OUT/lockstep.log"
: > "$OUT/neg_shift1.log"
c=0; for phase in 0 416; do "$OUT/base/Vtb_lite" +PHASE=$phase +SHIFT=1 >> "$OUT/neg_shift1.log" 2>&1 || c=1; done
if [ $c = 1 ]; then echo "NEGCTRL_CAUGHT shift=1 ($(grep -c LT_MISMATCH "$OUT/neg_shift1.log") mismatch lines)"; else echo "NEGCTRL_SURVIVED shift=1"; rc=1; fi
"${V[@]}" -DOT_MESO_CA_MUTANT_LITE --Mdir "$OUT/m_lite" "${SRC[@]}" > "$OUT/build_mut.log" 2>&1 || { echo MUTANT_BUILD_FAIL; rc=1; }
: > "$OUT/mut_lite.log"
c=0; for phase in 0 416; do "$OUT/m_lite/Vtb_lite" +PHASE=$phase >> "$OUT/mut_lite.log" 2>&1 || c=1; done
if [ $c = 1 ]; then echo "MUTANT_CAUGHT LITE ($(grep -c LT_MISMATCH "$OUT/mut_lite.log") mismatch lines)"; else echo "MUTANT_SURVIVED LITE"; rc=1; fi
echo "RC $rc"; exit $rc
