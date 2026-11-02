#!/bin/bash
set -euo pipefail
K=$(realpath "$1")
test -s "$K/DRT_INPUT_CLOSURE.json"
IMAGE=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
docker run --rm --memory=8g --memory-swap=8g --cpus=2 -e OT_PG_STRICT=1 -v "$K":/work -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc 'set -eo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm_drt.log 2>&1
python3 -I /work/patch_private_drt.py /OpenROAD-flow-scripts/flow/scripts --packet /work > /work/private_drt_runtime_receipt.json
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=2 do-5_2_route
' > "$K/run_drt_observational.log" 2>&1
