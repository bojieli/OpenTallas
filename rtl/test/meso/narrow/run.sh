#!/bin/bash
# R1-NARROW (KV-PVFIN-1 11-13): lock-step NARROW 1 vs 0 (q/ready/fault identical every clk edge, 0 cycles) over 11
# receiver phases x 266 ring forms; negative controls (narrow mutant one live bit short; +SHIFT=1 wrong declared
# latency) must FAIL; verilator lint NARROW 0 vs 1.  usage: run.sh OUT
set -uo pipefail
R=$(cd "$(dirname "$0")/../../../.." && pwd)
OUT=${1:?output directory}; mkdir -p "$OUT"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
V=(verilator --binary --timing --build -j 8 --top-module tb_narrow -Wno-fatal)
SRC=("$R/rtl/test/meso/narrow/tb_narrow.sv" "$R/rtl/common/ot_dp_clk_landing_ca.sv" "$R/rtl/common/ot_meso_fifo.sv" "$R/rtl/common/ot_dp_clk_landing.sv")
rc=0
for top in ot_dp_clk_landing_ca ot_dp_clk_landing_cas; do for nr in 0 1; do
  verilator --lint-only -Wall --top-module $top -GW=2 -GNARROW=$nr "${SRC[@]:1}" > "$OUT/lint_${top}_$nr.log" 2>&1
  echo "LINT $top W=2 NARROW=$nr warnings=$(grep -c '%Warning' "$OUT/lint_${top}_$nr.log") errors=$(grep -c '%Error' "$OUT/lint_${top}_$nr.log")"
done; done
"${V[@]}" --Mdir "$OUT/base" "${SRC[@]}" > "$OUT/build.log" 2>&1 || { echo BUILD_FAIL; tail -20 "$OUT/build.log"; exit 2; }
: > "$OUT/lockstep.log"
for phase in 0 41 83 125 208 400 416 433 624 791 830; do "$OUT/base/Vtb_narrow" +PHASE=$phase >> "$OUT/lockstep.log" 2>&1 || rc=1; done
echo "PASS_RUNS $(grep -c NARROW_PASS "$OUT/lockstep.log") of 11; MISMATCH_LINES $(grep -c NR_MISMATCH "$OUT/lockstep.log")"
c=0; for phase in 0 416; do "$OUT/base/Vtb_narrow" +PHASE=$phase +SHIFT=1 >> "$OUT/neg_shift1.log" 2>&1 || c=1; done
if [ $c = 1 ]; then echo "NEGCTRL_CAUGHT shift=1 ($(grep -c NR_MISMATCH "$OUT/neg_shift1.log") mismatch lines)"; else echo "NEGCTRL_SURVIVED shift=1"; rc=1; fi
"${V[@]}" -DOT_MESO_CA_MUTANT_NARROW --Mdir "$OUT/m_narrow" "${SRC[@]}" > "$OUT/build_mut.log" 2>&1 || { echo MUTANT_BUILD_FAIL; rc=1; }
c=0; for phase in 0 416; do "$OUT/m_narrow/Vtb_narrow" +PHASE=$phase >> "$OUT/mut_narrow.log" 2>&1 || c=1; done
if [ $c = 1 ]; then echo "MUTANT_CAUGHT NARROW ($(grep -c NR_MISMATCH "$OUT/mut_narrow.log") mismatch lines)"; else echo "MUTANT_SURVIVED NARROW"; rc=1; fi
echo "RC $rc"; exit $rc
