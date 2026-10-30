#!/bin/bash
set -eu
R=/srv/opentallas-scratch2/claude/codex-qc-clock-0336
W=/srv/opentallas-scratch2/claude/wt/codex-qc-clock-0336
docker run --rm --name codexqcclock-ideal-0336 --memory=32g --memory-swap=32g --cpus=4 -v "$R/ideal:/work" openroad/orfs:asap7lock bash -c "set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; for C in TT FF; do CORNER=\$C LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM openroad -exit /work/clock/ctree.tcl > /work/clock/ctree_\$C.log 2>&1; done; chown -R 1000:1000 /work"
for C in TT FF; do python3 "$W/tools/die_plan/trial_tap_arrivals.py" "$R/ideal/clock/tree.json" "$R/ideal/clock/arr_$C.txt" "$C" "$R/proof/tap_arrivals_$C.json" --clock-components --node-cell-names; done
