#!/bin/bash
set -euo pipefail
r=0
docker run --rm --cpus 2 --memory 16g --memory-swap 16g -v "$PWD":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/kit_modes.py check /work --step grt --session "tc bc" --hold-repair > /work/grt_mode_check.log
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/grt_mm_patch.log
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=2 HOLD_SLACK_MARGIN=10 do-5_1_grt
python3 -I /work/legacy_gate.py /work grt > /work/grt_policy.log 2>&1
' > grt_only.log 2>&1 || r=$?
printf '%s\n' "$r" > grt_only.rc
exit "$r"
