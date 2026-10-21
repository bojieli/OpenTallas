#!/usr/bin/env bash
# Reviewed existing-case checkpoint replay; no repair_design or GEN restart.
# Baseline is an immutable failed case; CANDIDATE_DIR contains reviewed fclk_audit.tcl.
set -euo pipefail
BASELINE_CASE=${BASELINE_CASE:-${H1_CASE:-}}
: "${BASELINE_CASE:?immutable failed case path}" "${CANDIDATE_DIR:?candidate helper directory}" "${REPLAY_OUT:?new output directory}"
D=$(cd "$(dirname "$0")" && pwd)
if test -d "$REPLAY_OUT" && test -n "$(find "$REPLAY_OUT" -type f -print -quit)"; then
 echo "Refuse existing replay output: $REPLAY_OUT" >&2; exit 2
fi
mkdir -p "$REPLAY_OUT"
expected_fclk=64dc1eb2a44494290f04ee7213ae65c2667a16ad4b05e2047a3d4fd54f06fd1d
actual_fclk=$(sha256sum "$CANDIDATE_DIR/fclk_audit.tcl" | awk '{print $1}')
if test "$actual_fclk" != "$expected_fclk"; then echo 'Published reviewed fclk source mismatch' >&2;exit 2;fi
sha256sum "$BASELINE_CASE/run.tcl" "$BASELINE_CASE/die_repeaters.tcl" \
 "$BASELINE_CASE/out/place.odb" "$BASELINE_CASE/die_repeaters.fclk.fail.odb" \
 "$BASELINE_CASE/die_repeaters.fclk.json" "$CANDIDATE_DIR/fclk_audit.tcl" > "$REPLAY_OUT/inputs.sha256"
docker image inspect openroad/orfs:asap7lock --format '{{.Id}} {{json .RepoDigests}}' > "$REPLAY_OUT/image.txt"
date -Is > "$REPLAY_OUT/started.txt"
for step in export_old_names replay; do
 docker run --rm --cpus=2 --memory=32g --memory-swap=32g \
  -v "$BASELINE_CASE:/baseline:ro" -v "$CANDIDATE_DIR:/candidate:ro" \
  -v "$D:/scripts:ro" -v "$REPLAY_OUT:/work" \
  openroad/orfs:asap7lock bash -lc \
  "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /scripts/$step.tcl > /work/$step.log 2>&1; rc=\$?; chmod -R a+rwX /work; exit \$rc"
done
