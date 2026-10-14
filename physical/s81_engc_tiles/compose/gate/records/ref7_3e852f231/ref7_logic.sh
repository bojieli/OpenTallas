#!/bin/bash
set -euo pipefail
S=/srv/opentallas-scratch/claude/el1013-engc-compose/ref7
B=$(find "$S/routes/ref7/work/orfs/results/asap7" -name 4_cts.odb -printf '%h\n')
test -n "$B"
for C in TT FF SS; do
  docker run --rm -e CORNER="$C" -e DB=4_cts.odb -e SDC=4_cts.sdc -v "$B":/base -v "$S/src":/src -v "$S":/diag openroad/orfs:asap7lock bash -c 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /diag/ref7_clock.tcl' > "$S/logic_${C}.out" 2>&1
 done
printf 'REPLAY_DONE\n'
