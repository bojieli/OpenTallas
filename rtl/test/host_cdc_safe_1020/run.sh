#!/bin/bash
set -eu
ROOT=$PWD;OUT=$ROOT/out_p192_2;mkdir -p "$OUT"
for case_name in exact tput mutant_addr mutant_bypass;do
 set +e
 bash rtl/test/host_cdc_safe_1020/bench_case.sh "$ROOT" "$OUT/$case_name" "$case_name"
 rc=$?
 set -e
 if [[ "$case_name" = exact || "$case_name" = tput ]];then
  [ "$rc" = 0 ] && grep -q '^PASS HOST_CDC_SAFE' "$OUT/$case_name/run.log"
 else
  [ "$rc" != 0 ] && grep -q '^FAIL SRAM transfer value mismatch' "$OUT/$case_name/run.log"
 fi
 grep -E '^(PASS|FAIL)' "$OUT/$case_name/run.log"
done
