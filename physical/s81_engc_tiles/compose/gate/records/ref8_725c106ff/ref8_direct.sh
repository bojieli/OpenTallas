#!/bin/bash
set -euo pipefail
S=/srv/opentallas-scratch/claude/el1013-engc-compose/ref8
B=$(find "$S/routes/ref8/work/orfs/results/asap7" -name 4_cts.odb -printf '%h\n')
test -n "$B"
for C in TT; do
  docker run --rm -e CORNER="$C" -e PATH_DELAY=max -e STRICT_BUDGET=150 -e DB=4_cts.odb -e SDC=4_cts.sdc -v "$B":/base -v "$S/src":/src -v "$S":/diag openroad/orfs:asap7lock bash -c 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /diag/ref8_direct.tcl' > "$S/direct_${C}.out" 2>&1
 done
printf 'REPLAY_DONE\n'
