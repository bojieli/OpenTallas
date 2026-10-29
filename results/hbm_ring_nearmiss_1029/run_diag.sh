#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-ring-nearmiss-1029
sudo docker run --rm --name codex-ring-nearmiss-diag --cpus=4 --memory=16g --memory-swap=16g -v "$D/kit":/work -v "$D":/out -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=4 RUN_SCRIPT=/out/diag.tcl RUN_LOG_NAME_STEM=nearmiss_diag run
' > "$D/diag.log" 2>&1
