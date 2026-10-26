#!/usr/bin/env bash
set -euo pipefail
OUT=$(realpath -m "$1");mkdir -p "$OUT";HERE=$(cd "$(dirname "$0")" && pwd)
bash "$HERE/run_sm_stage_bench.sh" "$OUT/positive"
for mutant in bank column;do
 if [[ "$mutant" == bank ]];then arg=-GMUT_BANK=1;else arg=-GMUT_COLUMN=1;fi
 rc=0
 bash "$HERE/run_sm_stage_bench.sh" "$OUT/$mutant" "$arg" || rc=$?
 if [[ "$rc" == 0 || "$rc" == 2 || "$rc" == 137 ]] || ! grep -q 'SM_STAGE data mismatch' "$OUT/$mutant/run.log";then
  echo "SM_STAGE MUTANT FAIL $mutant rc=$rc";exit 1
 fi
 echo "SM_STAGE MUTANT PASS $mutant"
done
echo 'SM_STAGE SUITE PASS'
