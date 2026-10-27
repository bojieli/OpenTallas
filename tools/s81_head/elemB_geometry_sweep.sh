#!/bin/bash
# Predict the reviewed pin/density successor before any CTS build.
# PLAN MODEL only. uf_phys3_v1 is the unchanged MODEL-REFIT-3 fit.
set -euo pipefail
P=$(realpath "$1")
G=$(realpath "$2")
FRINGE=${3:-8,1,6}
ARGS=()
if [ "$FRINGE" != none ]; then ARGS=(--fringe "$FRINGE"); fi
mkdir -p "$P/plans"
for fanouts in 2,4,4,4,4 4,4,2,4,4 4,4,4,4,2 4,4,4,2,2,2; do
  for balance in 0 1; do
    name=b_${fanouts//,/}_b${balance}
    if [ "$FRINGE" = none ]; then name=eq_$name; fi
    python3 -I "$P/head_tree_plan.py" "$G" "$P/plans/$name" \
      --entry 142.56,142.56 --seg 405 --fanouts "$fanouts" \
      --balance "$balance" "${ARGS[@]}" --halo 4.32 > "$P/plans/$name.plan.log" 2>&1
    python3 -I "$P/codex-head-p3_predict.py" "$P/codex-head-mr3" \
      "$P/plans/$name.tcl" "$P/plans/$name.seg.json" "$P/plans/$name.geo" \
      "$P/codex-head-lib" "$P/plans/$name.p3.json"
  done
done
