#!/bin/bash
# DISABLED PREP: parent must review exact capsule before any ot-run invocation.
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-cap-grt-prep-0742
K="$R/kit"
test "${CAP_REVIEWED_RELEASE:-0}" = 1 || { echo CAP_PREP_ONLY_NOT_RELEASED >&2; exit 90; }
cd "$K"
sha256sum -c FROZEN_INPUTS.sha256
test ! -e run_grt.log
docker run --rm --name cap-west2-grt-only-0742 --memory=16g --memory-swap=16g --cpus=4 -v "$K":/work -v "$K/baseline":/work/baseline:ro -w /OpenROAD-flow-scripts/flow -e OT_PG_STRICT=1 -e NUM_CORES=4 sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc '
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1
python3 -I /work/private_runtime_prepare.py /OpenROAD-flow-scripts/flow/scripts
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=4 CORNER=TC "CORNERS=tc bc" SKIP_INCREMENTAL_REPAIR=1 do-5_1_grt
' > "$K/run_grt.log" 2>&1
docker run --rm --network none --memory=8g --memory-swap=8g --cpus=1 -v "$K":/work sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python -threads 1 -exit /work/saved_check.py > "$K/saved_check.log" 2>&1
sha256sum -c FROZEN_INPUTS.sha256
echo CAP_GRT_ONLY_NO_DRT_FILL_FINISH
