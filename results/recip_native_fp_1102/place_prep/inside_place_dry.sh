#!/bin/bash
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /OpenROAD-flow-scripts/flow
if grep -q '^override export OT_HOLD_MM = 1' /work/config.mk; then
 python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/tmp/normal_mm_patch.log
fi
make -n DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=1 do-3_1_place_gp_skip_io do-3_2_place_iop do-3_3_place_gp do-3_4_place_resized do-3_5_place_dp do-3_place
