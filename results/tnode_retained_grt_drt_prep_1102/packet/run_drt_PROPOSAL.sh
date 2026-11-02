#!/usr/bin/env bash
set -euo pipefail
# PREP/HOLD. Owner must approve this exact finite observational scope first.
[[ ${TNODE_DRT_OWNER_RELEASED:-0} == 1 ]] || { echo 'PREP_ONLY: no Tnode DRT admission' >&2; exit 2; }
K=$(realpath "$1")
docker run --rm --memory=8g --memory-swap=8g --cpus=2 -e OT_PG_STRICT=1 -v "$K":/work sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl
python3 -I /work/patch_private_drt.py /OpenROAD-flow-scripts/flow/scripts --packet /work > /work/drt_runtime_patch.json
cd /OpenROAD-flow-scripts/flow
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=2 do-5_2_route
openroad -exit /work/check_saved.tcl > /work/drt_saved_pg.log 2>&1
'
