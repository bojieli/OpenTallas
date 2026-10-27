#!/bin/bash
# Use the HEAD standalone actual-interface contract; no clock/netlist edits.
set -euo pipefail
K=$(realpath "$1")
NICK=$2
for C in TT FF; do
  docker run --rm --memory 16g --memory-swap 16g --cpus 4 \
    -v "$K":/work -w /work -e OT_HEAD_NICK="$NICK" -e OT_CORNER="$C" \
    openroad/orfs:asap7lock bash -lc \
    'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 4 -exit /work/actual_head_sta.tcl' \
    > "$K/actual_sta_$C.log" 2>&1
  grep ACTUAL_HEAD_STA "$K/actual_sta_$C.log"
done
