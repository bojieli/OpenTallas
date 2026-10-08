#!/bin/bash
# Check preserved ORFS checkpoints and dry-run finish before route-only resume.
# Incomplete earlier stages require a separately reviewed next-stage resume.
set -u
O=$1; S=$2
fail() { echo "$1" >&2; echo RESUME_OK=0; exit "${2:-1}"; }
[ -d "$O/results" ] || fail 'Missing checkpoint results directory'
checkpoint=$(find "$O/results" -type f \( -name '*.odb' -o -name '1_2_yosys.v' \) -print -quit)
[ -n "$checkpoint" ] || fail 'No preserved ORFS checkpoint inventory'
out=$(docker run --rm -v "$S:/src:ro" -v "$O:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc \
  'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1 && make -n DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base finish 2>&1')
rc=$?
printf '%s\n' "$out"
[ "$rc" -eq 0 ] || fail "Dry-run command failed (rc=$rc)" "$rc"
st=$(printf '%s\n' "$out" | grep -oE 'do-[0-9]_[0-9]_[a-z_]+|[0-9]_[0-9]_[a-z_]+\.(log|tmp\.log)' | grep -oE '^(do-)?[0-9]_[0-9]_[a-z_]+' | sed 's/^do-//' | sort -u | tr '\n' ' ')
[ -n "$st" ] || fail 'No executable stage identified; finished or ambiguous dry-run requires separate review'
echo "STAGES_TO_RUN: $st"
first=$(printf '%s\n' "$st" | tr ' ' '\n' | sed '/^$/d' | sort | head -1)
echo "RESUME_FROM=$first"
case "$first" in 1_*|2_*|3_*|4_*) fail 'Dry-run would execute a pre-route stage';; *) echo RESUME_OK=1;; esac
