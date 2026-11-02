#!/bin/bash
set -euo pipefail
r=0
docker run --rm --cpus 2 --memory 16g --memory-swap 16g -v "$PWD":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/kit_modes.py check /work --step cts > /work/cts_mode_check.log
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/cts_mm_patch.log
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=2 do-cts
' > cts_native_only.log 2>&1 || r=$?
printf '%s\n' "$r" > cts_native_only.rc
exit "$r"
