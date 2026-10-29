#!/bin/bash
set -euo pipefail
K=$1
MEM=${3:-48}
CPUS=${4:-8}
docker run --rm --name codex-kv-astk-0828-grt --cpus "$CPUS" --memory "${MEM}g" --memory-swap "${MEM}g" -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm_grt.log 2>&1
python3 -I /work/kit_modes.py check /work --step grt --session "tc BC" --hold-repair > /work/grt_modes.log 2>&1
R=$(ls -d /work/run/results/asap7/*/base | head -1)
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 -o "$R/4_cts.odb" -o "$R/4_cts.sdc" grt HOLD_SLACK_MARGIN=10 > /work/grt.log 2>&1
' > "$K/run_grt.log" 2>&1
