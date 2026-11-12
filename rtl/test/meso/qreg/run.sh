#!/bin/bash
# CLAND-QREG-1: lock-step (q = gold delayed exactly 1 clk, ready/fault identical) over 11 phases x 20 ring forms,
# negative controls (bypass mutant, wrong declared shift 0 and 2), verilator lint QREG 0 vs 1.  usage: run.sh OUT
set -uo pipefail
R=$(cd "$(dirname "$0")/../../../.." && pwd)
OUT=${1:?output directory}; mkdir -p "$OUT"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
V=(verilator --binary --timing --build -j 8 --top-module tb_qreg -Wno-fatal)
SRC=("$R/rtl/test/meso/qreg/tb_qreg.sv" "$R/rtl/common/ot_dp_clk_landing_ca.sv" "$R/rtl/common/ot_meso_fifo.sv" "$R/rtl/common/ot_dp_clk_landing.sv")
rc=0
for top in ot_dp_clk_landing ot_dp_clk_landing_cas; do for qr in 0 1; do
  verilator --lint-only -Wall --top-module $top -GW=64 -GQREG=$qr "${SRC[@]:1}" > "$OUT/lint_${top}_$qr.log" 2>&1
  echo "LINT $top QREG=$qr warnings=$(grep -c '%Warning' "$OUT/lint_${top}_$qr.log")"
done; done
"${V[@]}" --Mdir "$OUT/base" "${SRC[@]}" > "$OUT/build.log" 2>&1 || { echo BUILD_FAIL; tail -20 "$OUT/build.log"; exit 2; }
: > "$OUT/lockstep.log"
for phase in 0 41 83 125 208 400 416 433 624 791 830; do "$OUT/base/Vtb_qreg" +PHASE=$phase >> "$OUT/lockstep.log" 2>&1 || rc=1; done
echo "PASS_RUNS $(grep -c QREG_PASS "$OUT/lockstep.log") of 11; MISMATCH_LINES $(grep -c QR_MISMATCH "$OUT/lockstep.log")"
for sh in 0 2; do
  c=0; for phase in 0 416; do "$OUT/base/Vtb_qreg" +PHASE=$phase +SHIFT=$sh >> "$OUT/neg_shift$sh.log" 2>&1 || c=1; done
  if [ $c = 1 ]; then echo "NEGCTRL_CAUGHT shift=$sh"; else echo "NEGCTRL_SURVIVED shift=$sh"; rc=1; fi
done
"${V[@]}" -DOT_MESO_MUTANT_QREG_BYPASS --Mdir "$OUT/m_bypass" "${SRC[@]}" > "$OUT/build_bypass.log" 2>&1 || { echo MUTANT_BUILD_FAIL; rc=1; }
c=0; for phase in 0 416; do "$OUT/m_bypass/Vtb_qreg" +PHASE=$phase >> "$OUT/mut_bypass.log" 2>&1 || c=1; done
if [ $c = 1 ]; then echo "MUTANT_CAUGHT QREG_BYPASS"; else echo "MUTANT_SURVIVED QREG_BYPASS"; rc=1; fi
echo "RC $rc"; exit $rc
