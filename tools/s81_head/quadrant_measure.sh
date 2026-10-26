#!/bin/bash
set -euo pipefail
K=$(realpath "$1")
LABEL=quadrant
[ "${OT_MEASURE_GRT:-0}" = 0 ] || LABEL=quadrant_grt
for C in TT FF; do
  docker run --rm --cpus=4 --memory=16g --memory-swap=16g -v "$K":/work -e OT_CORNER="$C" -e OT_MEASURE_GRT="${OT_MEASURE_GRT:-0}" \
    -e ODB=/work/run/results/asap7/hd_elemA_rb/base/4_seq.odb openroad/orfs:asap7lock bash -lc '
    source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
    cd /OpenROAD-flow-scripts/flow
    openroad -exit /work/quadrant_measure.tcl' > "$K/${LABEL}_${C}.log" 2>&1
  grep QMEASURE "$K/${LABEL}_${C}.log"
done
