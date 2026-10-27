#!/bin/bash
# Run normal ORFS incremental data hold repair in one fresh FF corner process.
# The caller stages an isolated copy of the accepted GRT/CTS kit.
set -euo pipefail
K=$(realpath "$1")
NICK=${2:-hd_elemA_rb}
MEM=${3:-32}
CPUS=${4:-16}
docker run --rm --memory="${MEM}g" --memory-swap="${MEM}g" --cpus="$CPUS" \
  -v "$K":/work -e OT_HEAD_NICK="$NICK" -e CPUS="$CPUS" \
  -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
    set -euo pipefail
    source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
    make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES="$CPUS" CORNER=BC CORNERS=bc do-5_1_grt
    for C in TT FF; do
      OT_CORNER="$C" openroad -threads 4 -exit /work/actual_head_sta.tcl > /work/repaired_sta_$C.log
    done
  ' > "$K/ff_repair.log" 2>&1
