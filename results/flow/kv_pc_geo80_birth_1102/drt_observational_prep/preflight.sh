#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-pc-geo80-birth-1102/drt_only
DK=docker; docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name codex-pc-drt-source-preflight-1102 --cpus=1 --memory=4g --memory-swap=4g -v "$D":/work -w /OpenROAD-flow-scripts/flow sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/orfs_hold_mm.py scripts /work/orfs_hold_mm.tcl >/work/preflight_mm.log 2>&1
python3 -I /work/patch_private_drt.py scripts --packet /work
make -n DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-5_2_route CORNER=TC "CORNERS=tc bc" > /work/DRY_DRT_ONLY.log
make -f Makefile -f /work/preflight.mk DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=1 pc_drt_preflight CORNER=TC "CORNERS=tc bc"
' > "$D/preflight.log" 2>&1
$DK run --rm -v "$D":/work sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 chown -R "$(id -u):$(id -g)" /work
