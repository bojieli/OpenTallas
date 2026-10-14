#!/bin/bash
set -euo pipefail
S=/srv/opentallas-scratch/claude/el1013-engc-compose/ref7
B=$(find "$S/routes/ref7/work/orfs/results/asap7" -name 4_cts.odb -printf '%h\n')
test -n "$B"
for C in TT FF SS; do
  for kind in max min; do
    for budget in 150 210; do
      if [[ $kind == min && $budget == 210 ]]; then continue; fi
      docker run --rm -e CORNER="$C" -e PATH_DELAY="$kind" -e STRICT_BUDGET="$budget" -e DB=4_cts.odb -e SDC=4_cts.sdc -v "$B":/base -v "$S/src":/src -v "$S":/diag openroad/orfs:asap7lock bash -c 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /diag/ref7_pairs.tcl' > "$S/pairs_${C}_${kind}_${budget}.out" 2>&1
    done
  done
  docker run --rm -e CORNER="$C" -e DB=4_cts.odb -e SDC=4_cts.sdc -v "$B":/base -v "$S/src":/src -v "$S/src/physical/s81_engc_tiles/compose/gate":/t openroad/orfs:asap7lock bash -c 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /t/ckpath.tcl' > "$S/ckp_${C}.out" 2>&1
 done
printf 'REPLAY_DONE\n'
