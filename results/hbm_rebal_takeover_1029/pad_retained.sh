#!/bin/bash
set -euo pipefail
K=$(cd "$(dirname "$0")/kit" && pwd)
docker run --rm --name codex-hnx-pad-retained-0310 --cpus 16 --memory 32g --memory-swap 32g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm_pad_retained.log 2>&1
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16 run RUN_SCRIPT=/work/cts_pad_retained.tcl > /work/pad_retained.log 2>&1
'
