#!/bin/bash
# KIT-OPS-6 lever 7 (FABLE-METHOD): run an OpenROAD Tcl script on a known-answer clock design.
#   run_openroad.sh SCRIPT.tcl [VAR=value ...]     (the clocktest dir is mounted at /ct, the repo tools/die_plan at /tools)
# Order: OT_CLOCKTEST_OPENROAD (a command prefix) > `openroad` on PATH > ot-run + docker openroad/orfs:asap7lock (the merge-queue host form).
set -eu
HERE=$(cd "$(dirname "$0")" && pwd); TOOLS=$(cd "$HERE/.." && pwd); S=$1; shift
ENVS=(); for kv in "$@"; do ENVS+=(-e "$kv"); done
IMG=${OT_CLOCKTEST_IMAGE:-openroad/orfs:asap7lock}
CMD="source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /ct/$(basename "$S")"
if [ -n "${OT_CLOCKTEST_OPENROAD:-}" ]; then exec $OT_CLOCKTEST_OPENROAD "$HERE/$(basename "$S")" ; fi
command -v docker >/dev/null || { echo "NO_OPENROAD"; exit 77; }
RUN=(docker run --rm --memory 8g -u "$(id -u):$(id -g)" -v "$HERE:/ct:ro" -v "$TOOLS:/tools:ro" -v "$TOOLS/../../physical/common_flow:/common:ro" "${ENVS[@]}" "$IMG" bash -lc "$CMD")
if [ -n "${OT_CLOCKTEST_OTRUN:-}" ] && command -v ot-run >/dev/null; then exec ot-run --mem 8 --threads 1 --dir "$HERE" --stage "$HERE" --stage "$TOOLS" -- "${RUN[@]}"; fi
exec "${RUN[@]}"
