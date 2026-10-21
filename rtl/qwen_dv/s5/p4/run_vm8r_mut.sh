#!/usr/bin/env bash
# QW2-VM8P4 10-21: ONE lp mutant of qfd_dv_s5_vm8r as a plain pass/fail command (exit 1 + "LP_LOCKSTEP FAIL" when the
# mutant is caught, exit 0 when it escapes).  Usage: run_vm8r_mut.sh OUTDIR MUT   (fleet only; SIM / VERILATOR as the lp bench)
set -u
cd "${LP_ROOT:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel)}"
OUT=$1; M=$2
MUTS=$M bash rtl/qwen_dv/s5/p4/lp/qfd_dv_s5_vm8r_bench.sh "$OUT" > "$OUT.bench.log" 2>&1
grep -o 'LP_LOCKSTEP [A-Z]*.*' "$OUT/mut$M.log" | head -1
grep -q 'LP_LOCKSTEP FAIL' "$OUT/mut$M.log" && exit 1
exit 0
