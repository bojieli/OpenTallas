#!/bin/bash
set -euo pipefail
r=0
docker run --rm -e OT_PG_STRICT=1 --cpus 2 --memory 16g --memory-swap 16g -v "$PWD":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/assert_mm_input.py > /work/mm_role_input_guard.log
python3 -I /work/kit_modes.py check /work --step grt --session "tc BC" --hold-repair > /work/grt_mode_check.log
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/grt_mm_patch.log
python3 -I /work/sc_wrap_honest_place_runtime.py /OpenROAD-flow-scripts/flow/scripts --driver /work/native_pg_birth_global_route.tcl > /work/sc_honest_place_runtime.json
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=2 HOLD_SLACK_MARGIN=10 do-5_1_grt
' > native_repair.log 2>&1 || r=$?
printf '%s\n' "$r" > native_repair.rc
if [ "$r" -ne 0 ]; then exit "$r"; fi
bash run_native_readout.sh
