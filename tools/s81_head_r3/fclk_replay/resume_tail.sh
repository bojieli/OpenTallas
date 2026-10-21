#!/usr/bin/env bash
set -euo pipefail
: "${BASELINE_CASE:?immutable original case}" "${REPAIRED_DIR:?immutable repaired output}" "${CANDIDATE_DIR:?published helper directory}" "${TAIL_OUT:?NEW output directory}"
D=$(cd "$(dirname "$0")" && pwd)
if test -d "$TAIL_OUT" && test -n "$(find "$TAIL_OUT" -type f -print -quit)"; then
 echo "Refuse to overwrite existing physical continuation artifacts: $TAIL_OUT" >&2; exit 2
fi
mkdir -p "$TAIL_OUT/out"
# Original run.sh uses MEMG=96 / CPUS=8; retain that admission unless measured fleet resources choose otherwise.
for phase in export_resume_state resume_tail; do
 docker run --rm --cpus="${CPUS:-8}" --memory="${MEMG:-96}g" --memory-swap="${MEMG:-96}g" \
  -v "$BASELINE_CASE:/baseline:ro" -v "$REPAIRED_DIR:/repair:ro" -v "$CANDIDATE_DIR:/candidate:ro" \
  -v "$D:/scripts:ro" -v "$TAIL_OUT:/work" openroad/orfs:asap7lock bash -lc \
  "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads ${CPUS:-8} -no_init -exit /scripts/$phase.tcl > /work/$phase.log 2>&1; rc=\$?; chmod -R a+rwX /work; exit \$rc"
done
