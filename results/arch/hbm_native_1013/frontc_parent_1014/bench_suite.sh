#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
bash bench_run.sh split > bench_positive.log 2>&1
cat bench_positive.log
set +e
bash bench_run.sh mut > bench_mutant.log 2>&1
rc=$?
set -e
cat bench_mutant.log
if [ "$rc" -eq 0 ] || ! grep -q 'frontC literal comparison mismatch' bench_mutant.log; then echo 'FRONTC_MUTANT_NOT_OBSERVED'; exit 1; fi
echo 'FRONTC_SUITE_PASS positive exact and observed wrong RAW mapping mutant'
