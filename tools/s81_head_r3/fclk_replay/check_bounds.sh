#!/usr/bin/env bash
set -euo pipefail
: "${BASELINE_CASE:?immutable failed case}" "${REPAIRED_DIR:?immutable repair output}" "${CANDIDATE_DIR:?published reviewed helper directory}" "${CHECK_OUT:?new output directory}"
D=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$CHECK_OUT"
docker run --rm --cpus=2 --memory=32g --memory-swap=32g -e CHECK_FAILED_BASELINE="${CHECK_FAILED_BASELINE:-0}" \
 -v "$BASELINE_CASE:/baseline:ro" -v "$REPAIRED_DIR:/repair:ro" \
 -v "$CANDIDATE_DIR:/candidate:ro" -v "$D:/scripts:ro" -v "$CHECK_OUT:/work" \
 openroad/orfs:asap7lock bash -lc \
 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /scripts/check_bounds.tcl > /work/check.log 2>&1; rc=$?; chmod -R a+rwX /work; exit $rc'
