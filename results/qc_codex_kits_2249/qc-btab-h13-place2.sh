#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-qc-kits-2249/btabH13
docker run --rm --memory=24g --cpus=8 -v "$D":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-3_3_place_gp && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 place' > "$D/place.log" 2>&1
