#!/usr/bin/env bash
# Preparation only until explicitly launched by the integration reviewer.
# Baseline is an immutable failed case; CANDIDATE_DIR contains reviewed fclk_audit.tcl.
set -euo pipefail
BASELINE_CASE=${BASELINE_CASE:-${H1_CASE:-}}
: "${BASELINE_CASE:?immutable failed case path}" "${CANDIDATE_DIR:?candidate helper directory}" "${REPLAY_OUT:?new output directory}"
D=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$REPLAY_OUT"
for step in export_old_names replay; do
 docker run --rm --cpus=2 --memory=32g --memory-swap=32g \
  -v "$BASELINE_CASE:/baseline:ro" -v "$CANDIDATE_DIR:/candidate:ro" \
  -v "$D:/scripts:ro" -v "$REPLAY_OUT:/work" \
  openroad/orfs:asap7lock bash -lc \
  "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /scripts/$step.tcl > /work/$step.log 2>&1; rc=\$?; chmod -R a+rwX /work; exit \$rc"
done
