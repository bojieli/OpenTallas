#!/bin/bash
set -euo pipefail
for q in 1 2 3; do
 bash tools/hbm_static/su_cxport_split_vl_run.sh out_q$q "$q" 1 0 0 0 1 9 1
 done
for mut in 4 5; do
 set +e
 bash tools/hbm_static/su_cxport_split_vl_run.sh out_mut$mut 0 1 "$mut" 1 0 1 9 1
 rc=$?
 set -e
 # This established bench uses $finish; its explicit FAIL verdict is authoritative.
 grep -q 'CXPORT_SPLIT FAIL' out_mut$mut/bench.log
 echo "EXPECTED_CAUSAL_FAIL mutant=$mut"
 done
