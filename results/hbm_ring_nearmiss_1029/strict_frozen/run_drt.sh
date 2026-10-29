#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-ring-nearmiss-1029
K="$D/kit_drt"
sudo docker run --rm --name codex-ring-drt-1029 --cpus=8 --memory=32g --memory-swap=32g -v "$K":/work -v "$D":/out -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm_current.log 2>&1 || exit 9
M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8"
$M RUN_SCRIPT=/out/prepare_drt.tcl RUN_LOG_NAME_STEM=prepare_drt run > /work/prepare_drt.log 2>&1 || exit 8
$M do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc > /work/drt.log 2>&1
rc=$?
if [ "$rc" = 0 ]; then $M do-finish > /work/finish.log 2>&1; rc=$?; fi
if [ "$rc" = 0 ]; then $M do-generate_abstract > /work/abstract.log 2>&1; rc=$?; fi
chown -R "$HUID:$HGID" /work
exit "$rc"
' > "$D/drt_client.log" 2>&1
