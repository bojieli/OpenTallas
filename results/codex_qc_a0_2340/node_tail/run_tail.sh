#!/bin/bash
set -euo pipefail
K=$1
# This scope stops after the warm GRT repair. Detailed route needs the new review.
docker run --rm --name codex-qca0-node-finalff-tail --cpus=8 --memory=32g --memory-swap=32g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl
cp /work/final_tail.tcl /OpenROAD-flow-scripts/flow/scripts/global_route.tcl
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 CORNER=TC CORNERS="tc BC" OT_HOLD_MM=1 OT_MM_SETUP_CORNER=tc do-5_1_grt
rc=$?;chown -R 1000:1000 /work;exit $rc' > "$K/final_tail_v3.log" 2>&1
