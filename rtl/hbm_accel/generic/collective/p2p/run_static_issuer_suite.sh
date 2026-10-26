#!/usr/bin/env bash
set -euo pipefail
OUT=$(realpath -m "$1");mkdir -p "$OUT"
HERE=$(cd "$(dirname "$0")" && pwd)
bash "$HERE/run_static_issuer_bench.sh" "$OUT/positive"
for mutant in data program;do
 case "$mutant" in
  data)arg=-GMUT_DATA=1;pattern='data mismatch';;
  program)arg=-GMUT_BRANCH=1;pattern='program mismatch';;
 esac
 rc=0;bash "$HERE/run_static_issuer_bench.sh" "$OUT/$mutant" "$arg" || rc=$?
 if [[ "$rc" != 1 ]] || ! grep -q "$pattern" "$OUT/$mutant/run.log";then
  echo "STATIC_ISSUER SUITE FAIL mutant=$mutant rc=$rc";exit 1
 fi
 echo "STATIC_ISSUER MUTANT PASS $mutant"
done
echo 'STATIC_ISSUER SUITE PASS'
