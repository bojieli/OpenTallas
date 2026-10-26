#!/usr/bin/env bash
set -euo pipefail
OUT=$(realpath -m "$1");mkdir -p "$OUT";HERE=$(cd "$(dirname "$0")" && pwd)
bash "$HERE/run_sm_stage_profiles_bench.sh" "$OUT/positive"
for mutant in bank column epoch read;do
 case "$mutant" in bank) arg=-GMUT_BANK=1;pattern='RAW_STAGE data mismatch';;
 column) arg=-GMUT_COLUMN=1;pattern='RAW_STAGE data mismatch';;
 epoch) arg=-GMUT_EPOCH=1;pattern='RAW_STAGE epoch mismatch';;
 read) arg=-GMUT_READ_DROP=1;pattern='RAW_STAGE data mismatch';;esac
 rc=0
 bash "$HERE/run_sm_stage_profiles_bench.sh" "$OUT/$mutant" -GRAW_ONLY=1 "$arg" || rc=$?
 if [[ "$rc" == 0 || "$rc" == 2 || "$rc" == 137 ]] || ! grep -q "$pattern" "$OUT/$mutant/run.log";then
  echo "RAW_STAGE MUTANT FAIL $mutant rc=$rc";exit 1
 fi
 echo "RAW_STAGE MUTANT PASS $mutant"
done
echo 'RAW_STAGE SUITE PASS'
