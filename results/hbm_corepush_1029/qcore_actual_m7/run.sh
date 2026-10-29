#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-qcore-actualm7-1029
sudo docker run --rm --name codex-qcore-actualm7-grt -v "$PWD/kit":/work -v "$PWD":/trial -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -e
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl
python3 -I /work/kit_modes.py check /work --step grt --session "tc bc" --hold-repair
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 GLOBAL_ROUTE_ARGS="-congestion_iterations 50 -verbose" do-grt
' > "$PWD/grt_actual_m7.log" 2>&1
