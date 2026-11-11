#!/bin/bash
# GUARD-REG-1 ring bench: gold STATUS_REG 0 / mid STATUS_REG 1 / cand STATUS_REG 1 + GUARD_REG 1, lock-step + mutants.
# usage: run.sh OUT
set -uo pipefail
R=$(cd "$(dirname "$0")/../../../.." && pwd)
OUT=${1:?output directory}; mkdir -p "$OUT"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
V=(verilator --binary --timing --build -j 8 --top-module tb_guard_reg -Wno-fatal)
SRC=("$R/rtl/test/meso/guard_reg/tb_guard_reg.sv" "$R/rtl/common/ot_dp_clk_landing_ca.sv" "$R/rtl/common/ot_meso_fifo.sv" "$R/rtl/common/ot_dp_clk_landing.sv")
"${V[@]}" --Mdir "$OUT/base" "${SRC[@]}" > "$OUT/build.log" 2>&1 || { echo BUILD_FAIL; tail -20 "$OUT/build.log"; exit 2; }
rc=0; : > "$OUT/lockstep.log"
PHASES="0 41 83 125 208 300 416 500 624 708 791"
for phase in $PHASES; do "$OUT/base/Vtb_guard_reg" +PHASE=$phase >> "$OUT/lockstep.log" 2>&1 || rc=1; done
for m in SR_GUARD GR_OH GR_LATE; do
  "${V[@]}" -DOT_MESO_CA_MUTANT_$m --Mdir "$OUT/m_$m" "${SRC[@]}" > "$OUT/build_$m.log" 2>&1 || { echo "MUTANT_BUILD_FAIL $m"; rc=1; continue; }
  c=0; : > "$OUT/mut_$m.log"
  for phase in $PHASES; do "$OUT/m_$m/Vtb_guard_reg" +PHASE=$phase >> "$OUT/mut_$m.log" 2>&1 || c=1; done
  if [ $c = 1 ]; then echo "MUTANT_CAUGHT $m $(grep -c GR_MISMATCH "$OUT/mut_$m.log")"; else echo "MUTANT_SURVIVED $m"; rc=1; fi
done
echo "PASS_PHASES $(grep -c GUARD_REG_PASS "$OUT/lockstep.log") / $(echo $PHASES | wc -w)"
echo "RC $rc"; exit $rc
