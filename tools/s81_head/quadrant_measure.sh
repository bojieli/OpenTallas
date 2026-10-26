#!/bin/bash
set -euo pipefail
K=$(realpath "$1")
for C in TT FF; do
  docker run --rm --cpus=4 --memory=16g --memory-swap=16g -v "$K":/work -e OT_CORNER="$C" \
    -e ODB=/work/run/results/asap7/hd_elemA_rb/base/4_seq.odb openroad/orfs:asap7lock bash -lc '
    source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
    cd /OpenROAD-flow-scripts/flow
    openroad -exit /work/quadrant_measure.tcl' > "$K/quadrant_${C}.log" 2>&1
  grep QMEASURE "$K/quadrant_${C}.log"
done
