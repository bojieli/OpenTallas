#!/bin/bash
# RING-LITE-2 (FABLE-KV-DIE 11-22): lock-step LITE 1 / CONTROL_STATUS_COPY 0 vs LITE 0 / CONTROL_STATUS_COPY 1 (q identical
# every clk edge, 0 cycles) over 11 receiver phases; negative controls (+SHIFT=1; lite mutant) must FAIL.  usage: run_csc.sh OUT
set -uo pipefail
R=$(cd "$(dirname "$0")/../../../.." && pwd)
OUT=${1:?output directory}; mkdir -p "$OUT"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
V=(verilator --binary --timing --build -j 8 --top-module tb_lite_csc -Wno-fatal)
SRC=("$R/rtl/test/meso/lite/tb_lite_csc.sv" "$R/rtl/common/ot_dp_clk_landing_ca.sv" "$R/rtl/common/ot_meso_fifo.sv" "$R/rtl/common/ot_dp_clk_landing.sv")
rc=0
"${V[@]}" --Mdir "$OUT/base" "${SRC[@]}" > "$OUT/build.log" 2>&1 || { echo BUILD_FAIL; tail -20 "$OUT/build.log"; exit 2; }
: > "$OUT/lockstep.log"
for phase in 0 41 83 125 208 400 416 433 624 791 830; do "$OUT/base/Vtb_lite_csc" +PHASE=$phase >> "$OUT/lockstep.log" 2>&1 || rc=1; done
echo "PASS_RUNS $(grep -c LITE_PASS "$OUT/lockstep.log") of 11; MISMATCH_LINES $(grep -c LT_MISMATCH "$OUT/lockstep.log")"
grep LITE_PASS "$OUT/lockstep.log"
: > "$OUT/neg_shift1.log"
c=0; for phase in 0 416; do "$OUT/base/Vtb_lite_csc" +PHASE=$phase +SHIFT=1 >> "$OUT/neg_shift1.log" 2>&1 || c=1; done
if [ $c = 1 ]; then echo "NEGCTRL_CAUGHT shift=1 ($(grep -c LT_MISMATCH "$OUT/neg_shift1.log") mismatch lines)"; else echo "NEGCTRL_SURVIVED shift=1"; rc=1; fi
"${V[@]}" -DOT_MESO_CA_MUTANT_LITE --Mdir "$OUT/m_lite" "${SRC[@]}" > "$OUT/build_mut.log" 2>&1 || { echo MUTANT_BUILD_FAIL; rc=1; }
: > "$OUT/mut_lite.log"
c=0; for phase in 0 416; do "$OUT/m_lite/Vtb_lite_csc" +PHASE=$phase >> "$OUT/mut_lite.log" 2>&1 || c=1; done
if [ $c = 1 ]; then echo "MUTANT_CAUGHT LITE ($(grep -c LT_MISMATCH "$OUT/mut_lite.log") mismatch lines)"; else echo "MUTANT_SURVIVED LITE"; rc=1; fi
echo "RC $rc"; exit $rc
