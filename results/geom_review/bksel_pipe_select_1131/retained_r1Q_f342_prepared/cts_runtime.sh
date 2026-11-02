#!/bin/bash
set -euo pipefail
trap 'r=$?; chown -R "${HUID:-1000}:${HGID:-1000}" /work 2>/dev/null || true; exit "$r"' EXIT
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /retained-api/retained_stage.py check-makefile /OpenROAD-flow-scripts/flow/Makefile
python3 -I /work/kit_modes.py check /work --step cts > /work/retained_cts_modes.log 2>&1
rc=0
if [ $rc = 0 ] && grep -q '^override export OT_HOLD_MM = 1' /work/config.mk; then python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1 || { cat /work/orfs_hold_mm.log; echo 'KIT_MODES FAIL orfs_hold_mm patch'; rc=9; }; fi; 
[ "$rc" = 0 ] || exit "$rc"
cd /OpenROAD-flow-scripts/flow
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-cts
