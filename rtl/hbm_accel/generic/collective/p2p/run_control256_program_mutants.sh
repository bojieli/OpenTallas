#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=${HCOLL_ROOT:-$(git -C "$HERE" rev-parse --show-toplevel)}
OUT=${1:?output directory};mkdir -p "$OUT"
P=$ROOT/rtl/hbm_accel/generic/collective/p2p
for mode in data half;do
 args=();[[ $mode != data ]] || args+=(-GMUT_DATA=1);[[ $mode != half ]] || args+=(-GMUT_HALF=1)
 set +e
 "$P/run_control256_program_bench.sh" "$OUT/$mode" "${args[@]}" > "$OUT/$mode.log" 2>&1
 rc=$?
 set -e
 [[ $rc != 0 ]];grep -q 'CONTROL mismatch' "$OUT/$mode/run.log"
 echo "CONTROL256_PROGRAM MUTANT PASS $mode intended_control_rejection exit=$rc"
done
