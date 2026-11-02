#!/bin/bash
set -euo pipefail
MODE=${1:-dry}
case "$MODE" in dry|run) ;; *) exit 64 ;; esac
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /OpenROAD-flow-scripts/flow
python3 -I /work/orfs_hold_mm.py scripts > /case/CTS_NORMAL_MM_PATCH.log
python3 -I /case/patch_cts_entry.py scripts /case/NORMAL_SCRIPT_READSET.json /case/CTS_ENTRY_PATCH.json
args=(DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=1)
targets=(do-4_1_cts do-4_cts)
if [ "$MODE" = dry ]; then
 make -n "${args[@]}" "${targets[@]}"
else
 make "${args[@]}" "${targets[@]}"
fi
