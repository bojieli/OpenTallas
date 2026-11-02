#!/bin/bash
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /OpenROAD-flow-scripts/flow
args=(DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=1)
targets=(do-2_1_floorplan do-2_2_floorplan_macro do-2_3_floorplan_tapcell do-2_4_floorplan_pdn do-2_floorplan do-2_floorplan.sdc)
if [ "$1" = dry ]; then
  make -n "${args[@]}" "${targets[@]}"
else
  make "${args[@]}" "${targets[@]}"
fi
