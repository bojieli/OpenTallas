#!/bin/bash
set -eu
R=/srv/opentallas-scratch2/claude/codex-qc-clock-0336
W=/srv/opentallas-scratch2/claude/wt/codex-qc-clock-0336
for C in TT FF; do python3 "$W/tools/die_plan/trial_tap_arrivals.py" "$R/ideal/clock/tree_full.json" "$R/ideal/clock/arr_$C.txt" "$C" "$R/proof/tap_arrivals_$C.json" --clock-components --node-cell-names; done
