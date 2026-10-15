#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
case_run() {
 local label=$1 defs=$2 expect=$3 rc=0
 bash tools/s81_vm/core_leaf_bench.sh "$PWD/out/$label" "$label" "$defs" > "$label.log" 2>&1 || rc=$?
 tail -n 4 "$label.log"
 if [ "$expect" = pass ]; then
  test "$rc" = 0
  grep -q "CORE_LEAF PASS $label" "$label.log"
 else
  test "$rc" != 0
  grep -q "COMMIT MISMATCH" "out/$label/run.log"
  grep -q "CORE_LEAF FAIL $label" "$label.log"
 fi
}
case_run baseline 'OT_VM_NATIVE_READ_L16' pass
case_run scatter1 'OT_VM_NATIVE_READ_L16 OT_VM_NATIVE_WSCATTER' pass
case_run early_commit 'OT_VM_NATIVE_READ_L16 OT_VM_NATIVE_WSCATTER OT_VM_BANK_MUT_EARLY_COMMIT' fail
printf 'NATIVE_SCATTER_CORE_GATE PASS baseline_K11 staged_K12 early_commit_mutant_rejected\n'
