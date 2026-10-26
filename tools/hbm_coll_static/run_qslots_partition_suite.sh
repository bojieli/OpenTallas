#!/usr/bin/env bash
set -euo pipefail
out=$1
mkdir -p "$out"
for npt in 3 2; do
    bash tools/hbm_coll_static/run_qslots_partition_gate.sh "$npt" positive "$out/q${npt}_positive" > "$out/q${npt}_positive.log" 2>&1
    cat "$out/q${npt}_positive.log"
    for mut in select latency; do
        set +e
        bash tools/hbm_coll_static/run_qslots_partition_gate.sh "$npt" "$mut" "$out/q${npt}_${mut}" > "$out/q${npt}_${mut}.log" 2>&1
        mutant_rc=$?
        set -e
        cat "$out/q${npt}_${mut}.log"
        test "$mutant_rc" -ne 0
        grep -q "QSLOTS_PARTITION mismatch NPT=$npt cycle=3 payload=1" "$out/q${npt}_${mut}.log"
        grep -q 'kind=0/0' "$out/q${npt}_${mut}.log"
    done
done
echo QSLOTS_PARTITION_SUITE_PASS
