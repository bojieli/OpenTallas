#!/bin/bash
set -euo pipefail
r=0
docker run --rm --cpus 2 --memory 16g --memory-swap 16g -v "$PWD":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/patch_sc_place.py /OpenROAD-flow-scripts/flow/scripts > /work/sc_native_input_patch.log
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/sc_mm_patch.log
openroad -exit /work/correct_and_rebind.tcl > /work/correct_and_rebind.log 2>&1
P=$(find /work/run/results/asap7 -path "*/base/3_place.odb" -print -quit)
cp /work/sc_place_corrected.odb "${P%/*}/sc_place_corrected.odb"
M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=2"
$M do-3_3_place_gp
$M do-3_5_place_dp
$M do-3_place
' > place_correction.log 2>&1 || r=$?
printf '%s\n' "$r" > place_correction.rc
exit "$r"
