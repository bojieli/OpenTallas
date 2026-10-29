#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-qcore-1028
docker run --rm --name codex-qcore-symmetric-place --cpus=8 --memory=24g --memory-swap=24g -v "$PWD/kit":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 place
'
