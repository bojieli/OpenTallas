#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "$1");mkdir -p "$OUT"
P=$ROOT/rtl/hbm_accel/generic/collective/p2p
"$P/run_static_program_target_bench.sh" "$OUT/positive" > "$OUT/positive.log" 2>&1
set +e
"$P/run_static_program_target_bench.sh" "$OUT/mut_data" -GMUT_DATA=1 > "$OUT/mut_data.log" 2>&1
rc=$?
set -e
if [[ $rc == 0 ]] || ! grep -q 'DATA mismatch' "$OUT/mut_data/run.log";then
 echo 'PROGRAM_JOIN mutant failed to reject at intended data check';exit 1
fi
if grep -Eq '%Warning-(MULTIDRIVEN|LATCH|UNOPTFLAT)' "$OUT/positive/build.log";then
 echo 'PROGRAM_JOIN structural lint warning';exit 1
fi
grep '^PROGRAM_JOIN' "$OUT/positive/run.log"
for scenario in $(seq 1 20);do grep '^PROGRAM_JOIN FAULT PASS' "$OUT/positive/fault-$scenario.log";done
echo "PROGRAM_JOIN MUTANT PASS intended_data_rejection exit=$rc"
