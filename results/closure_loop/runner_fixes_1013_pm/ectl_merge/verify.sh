#!/bin/bash
set -u
bash tools/qwen_kv_die/ectl3_bench.sh checks/exact > checks_exact.log 2>&1
pos=$?
S=0 E=0 bash tools/qwen_kv_die/ectl3_bench.sh checks/mut C > checks_mut.log 2>&1
mut=$?
printf 'positive_rc=%s\nmutant_rc=%s\n' "$pos" "$mut" > checks.rc
cat checks.rc
[ "$pos" = 0 ] && [ "$mut" = 1 ] && grep -q '^ECTL3 FAIL lockstep' checks/mut/ectl3_C.log
