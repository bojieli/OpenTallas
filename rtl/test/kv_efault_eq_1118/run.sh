#!/bin/bash
# KV-EFAULT-EQ 11-18: eq-pipe equivalence of ot_dp_efault.  usage: run.sh [OUTDIR]  (Verilator; run it through ot-run, not on intel2/localhost)
set -u
R=$(cd "$(dirname "$0")/../../.." && pwd); OUT=${1:-/tmp/kv_efault_eq_1118}; mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=$(command -v verilator)
NF=0
for m in 0 1 2; do
  "$V" --binary -j 4 --timing -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_ot_dp_efault_eqpipe -GMUT=$m \
    -Mdir "$OUT/m$m" -o Vtb "$R/rtl/test/kv_efault_eq_1118/tb_ot_dp_efault_eqpipe.sv" "$R/rtl/lib/ot_dp_efault.sv" > "$OUT/m$m.build.log" 2>&1 || { echo "BUILD_FAIL MUT $m"; NF=$((NF+1)); continue; }
  "$OUT/m$m/Vtb" > "$OUT/m$m.log" 2>&1
  if [ $m = 0 ]; then grep -m1 "^PASS" "$OUT/m$m.log" || { echo "FAIL MUT 0"; head -5 "$OUT/m$m.log"; NF=$((NF+1)); }
  else grep -m1 "^FAIL" "$OUT/m$m.log" | sed 's/^/CAUGHT /' || true; grep -q "^FAIL" "$OUT/m$m.log" || { echo "MISSED MUT $m"; NF=$((NF+1)); }; fi
done
"$V" --lint-only -Wall --top-module ot_dp_efault "$R/rtl/lib/ot_dp_efault.sv" > "$OUT/lint_default.log" 2>&1 && echo "LINT default clean" || { echo "LINT default FAIL"; head "$OUT/lint_default.log"; NF=$((NF+1)); }
"$V" --lint-only -Wall --top-module ot_dp_efault -GN=12 -GAGE=13 '-GEQ_PIPE_V=48'"'"'h000000000211' "$R/rtl/lib/ot_dp_efault.sv" > "$OUT/lint_pipe.log" 2>&1 && echo "LINT pipe clean" || { echo "LINT pipe FAIL"; head "$OUT/lint_pipe.log"; NF=$((NF+1)); }
echo "SUMMARY fail $NF"; [ $NF = 0 ]
