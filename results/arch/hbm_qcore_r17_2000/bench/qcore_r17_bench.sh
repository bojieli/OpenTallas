#!/usr/bin/env bash
set -euo pipefail
form=$1
mkdir -p "out_row$form"
ROW_EN=$form bash tools/hbm_static/qcore_r13_lockstep_run.sh "out_row$form/m0" 0 > "out_row$form/m0.driver.log" 2>&1
cat "out_row$form/m0/bench.log"
for mut in 256 128; do
 set +e
 ROW_EN=$form bash tools/hbm_static/qcore_r13_lockstep_run.sh "out_row$form/m$mut" "$mut" > "out_row$form/m$mut.driver.log" 2>&1
 actual_rc=$?
 set -e
 test "$actual_rc" -eq 0
 grep -q 'QCORE_RG FAIL' "out_row$form/m$mut/bench.log"
 echo "QCORE_ROW$form MUT$mut REJECTED actual_rc=$actual_rc"
done
echo "QCORE_ROW$form GATE PASS"
