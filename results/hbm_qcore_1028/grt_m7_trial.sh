#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-qcore-m7-1029
grep -q '^OT_HOLD_GATE PASS ' postcts_hold.log
docker run --rm --name codex-qcore-m7-grt --cpus=8 --memory=32g --memory-swap=32g -v "$PWD/kit":/work -v "$PWD":/trial -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -e
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl
python3 -I /work/kit_modes.py check /work --step grt --session "tc bc" --hold-repair
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-grt
'
