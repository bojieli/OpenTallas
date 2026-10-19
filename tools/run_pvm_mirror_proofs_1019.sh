#!/bin/bash
set -euo pipefail
out=${1:?};mkdir -p "$out";out=$(realpath "$out")
run(){
 local name=$1 expected=$2;shift 2
 if bash rtl/hbm_accel/sm/attn/test/run_pv_merge_s3_bench.sh "$out/$name" "$@" > "$out/$name.log" 2>&1;then
  test "$expected" = pass || { echo "MUTANT_SURVIVED $name";exit 1; }
  grep '^PVM PASS' "$out/$name/check.log"
 else
  test "$expected" = fail || { tail -20 "$out/$name.log";exit 1; }
  grep -E '^PVM FAIL mismatches=[1-9]' "$out/$name/check.log"
 fi
}
run exact pass 0 1 0 0
run tight pass 0 1 1 0
run mut1 fail 1 1 0 0
run mut4 fail 4 1 0 0
run mut5 fail 5 1 0 0
run pubearly fail 0 1 1 1
