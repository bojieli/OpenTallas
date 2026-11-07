#!/bin/bash
# STATUS-REG-1 lock-step + mutants. usage: run.sh OUT
set -uo pipefail
R=$(cd "$(dirname "$0")/../../../.." && pwd)
OUT=${1:?output directory}; mkdir -p "$OUT"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
V=(verilator --binary --timing --build -j 8 --top-module tb_status_reg -Wno-fatal)
SRC=("$R/rtl/test/meso/status_reg/tb_status_reg.sv" "$R/rtl/common/ot_dp_clk_landing_ca.sv" "$R/rtl/common/ot_meso_fifo.sv" "$R/rtl/common/ot_dp_clk_landing.sv")
"${V[@]}" --Mdir "$OUT/base" "${SRC[@]}" > "$OUT/build.log" 2>&1 || { echo BUILD_FAIL; tail -20 "$OUT/build.log"; exit 2; }
rc=0; : > "$OUT/lockstep.log"
for phase in 0 41 83 125 208 416 624 791; do "$OUT/base/Vtb_status_reg" +PHASE=$phase >> "$OUT/lockstep.log" 2>&1 || rc=1; done
for m in SR_ARM SR_OH SR_TAG SR_GUARD; do
  "${V[@]}" -DOT_MESO_CA_MUTANT_$m --Mdir "$OUT/m_$m" "${SRC[@]}" > "$OUT/build_$m.log" 2>&1 || { echo "MUTANT_BUILD_FAIL $m"; rc=1; continue; }
  c=0; : > "$OUT/mut_$m.log"
  for phase in 0 125 416 624; do "$OUT/m_$m/Vtb_status_reg" +PHASE=$phase >> "$OUT/mut_$m.log" 2>&1 || c=1; done
  if [ $c = 1 ]; then echo "MUTANT_CAUGHT $m"; else echo "MUTANT_SURVIVED $m"; rc=1; fi
done
grep -c STATUS_REG_PASS "$OUT/lockstep.log"
echo "RC $rc"; exit $rc
