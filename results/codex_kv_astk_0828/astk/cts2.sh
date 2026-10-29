#!/bin/bash
set -euo pipefail
K=/srv/opentallas-scratch2/claude/codex-kv-astk-0828/kit_status2
docker run --rm --name codex-kv-astk-0828-cts2 --cpus 8 --memory 48g --memory-swap 48g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
R=$(ls -d /work/run/results/asap7/*/base | head -1)
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 -o "$R/3_place.odb" -o "$R/3_place.sdc" cts > /work/cts.log 2>&1
'
