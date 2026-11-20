#!/bin/bash
# KV-PLAN-R2 11-20 (EFAULT-STAGE): staged-efault equivalence (iverilog, small).  usage: run.sh [OUTDIR]
set -u
R=$(cd "$(dirname "$0")/../../.." && pwd); OUT=${1:-/tmp/kv_efault_stage_1120}; mkdir -p "$OUT"
python3 -I -c "import sys; sys.path.insert(0, sys.argv[1]); import bind_pad_tail_split as T; print(T.KEEP_CELL)" \
  "$R/tools/die_plan" > "$OUT/ot_dp_dly_keep.sv" || { echo "FAIL keep cell"; exit 1; }
NF=0
for m in 0 1 2; do
  iverilog -g2012 -s tb_ot_dp_efault_stage -P tb_ot_dp_efault_stage.MUT=$m -o "$OUT/m$m.vvp" \
    "$R/rtl/test/kv_efault_stage_1120/tb_ot_dp_efault_stage.sv" "$R/rtl/lib/ot_dp_efault.sv" "$OUT/ot_dp_dly_keep.sv" \
    > "$OUT/m$m.build.log" 2>&1 || { echo "BUILD_FAIL MUT $m"; head -5 "$OUT/m$m.build.log"; NF=$((NF+1)); continue; }
  vvp -n "$OUT/m$m.vvp" > "$OUT/m$m.log" 2>&1
  if [ $m = 0 ]; then grep -m1 "^PASS" "$OUT/m$m.log" || { echo "FAIL MUT 0"; head -5 "$OUT/m$m.log"; NF=$((NF+1)); }
  else grep -m1 "^FAIL" "$OUT/m$m.log" | sed 's/^/CAUGHT /' || true; grep -q "^FAIL" "$OUT/m$m.log" || { echo "MISSED MUT $m"; NF=$((NF+1)); }; fi
done
echo "SUMMARY fail $NF"; [ $NF = 0 ]
