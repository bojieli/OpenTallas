#!/bin/bash
set -euo pipefail
MODE=${1:-dry}
case "$MODE" in dry|run) ;; *) exit 64 ;; esac
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /OpenROAD-flow-scripts/flow
if grep -q '^override export OT_HOLD_MM = 1' /work/config.mk; then
 python3 -I /work/orfs_hold_mm.py scripts > /case/CANARY_NORMAL_MM_PATCH.log
fi
python3 -I /case/patch_place_entries.py scripts /case/CANARY_ENTRY_PATCH.json /case/NORMAL_SCRIPT_READSET.json
args=(DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=1)
targets=(do-3_1_place_gp_skip_io do-3_2_place_iop do-3_3_place_gp do-3_4_place_resized do-3_5_place_dp do-3_place)
if [ "$MODE" = dry ]; then
 make -n "${args[@]}" "${targets[@]}"
else
 make "${args[@]}" "${targets[@]}"
fi
