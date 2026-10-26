#!/bin/bash
# S81U-2: differential bench of the per-head softmax tap ot_s81_su_smq vs the 2-head stop tap ot_s81_su_smt.
#   bash tools/s81_su_sm/smq_bench.sh OUTDIR MUT [TI SEED]     (MUT 0 = base: PASS; 1..3 = mutants: FAIL)
# The verdict line "SMQ PASS ..." / "SMQ FAIL ..." is printed LAST and unconditionally.
set -u
OUT=$1; MUT=$2; TI=${3:-5}; SEED=${4:-1017}
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$OUT"
iverilog -g2012 -s tb_s81_su_smq -P tb_s81_su_smq.MUT=$MUT -P tb_s81_su_smq.TI=$TI -P tb_s81_su_smq.SEED=$SEED -o "$OUT/smq.vvp" \
  "$ROOT/rtl/dsrom_sys/s81_dv/su_sm/test/tb_s81_su_smq.sv" "$ROOT/rtl/dsrom_sys/s81_dv/su_sm/ot_s81_su_smq.sv" \
  "$ROOT/rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_sm.sv" > "$OUT/build.log" 2>&1
rc=$?
if [ $rc -ne 0 ]; then tail -5 "$OUT/build.log"; echo "SMQ FAIL MUT=$MUT build rc=$rc"; exit 1; fi
vvp -n "$OUT/smq.vvp" > "$OUT/run.log" 2>&1
grep -v "^SMQ PASS\|^SMQ FAIL" "$OUT/run.log" | tail -14
V=$(grep -E "^SMQ (PASS|FAIL)" "$OUT/run.log" | tail -1)
[ -n "$V" ] || V="SMQ FAIL MUT=$MUT no verdict"
echo "$V"
case "$V" in "SMQ PASS"*) exit 0;; *) exit 1;; esac
