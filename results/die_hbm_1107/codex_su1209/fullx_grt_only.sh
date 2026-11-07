#!/bin/bash
# First GRT of fullx vL; existing CTS physical rc0 and exact native proof owner retained.
set -euo pipefail
cd /
K=/srv/opentallas-scratch2/claude/codex-su-1209/fullx_vL_cts_release
mkdir -p "$K/vis_grt"
touch "$K/vis_grt/.keep"
grep -q '^override export OT_HOLD_MM = 1' "$K/config.mk"
# No new LEC or config edit: command-line scope changes only the physical repair population.
docker run --rm --name "codex-fullxl-firstgrt-$$" --memory 16g --memory-swap 16g --cpus 8 -v "$K:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/vis_grt/runtime_patch.log 2>&1
python3 -I /work/kit_modes.py check /work --step grt --session "tc bc" --hold-repair > /work/vis_grt/kit_modes.log 2>&1
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 grt HOLD_SLACK_MARGIN=0 OT_HOLD_REPAIR_SCOPE=nonport > /work/run_grt_nonport.log 2>&1
'
