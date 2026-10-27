#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-hbm-clock-1351
K="$D/kit_vmdel_centre"
docker run --rm --cpus=8 --memory=24g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-floorplan
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-place
' > "$D/place.log" 2>&1
