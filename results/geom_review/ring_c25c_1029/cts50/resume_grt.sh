#!/bin/bash
set -euo pipefail
K=/srv/opentallas-scratch2/claude/codex-hbm-ring-1029/kits_v2/ot_hfd_coll_q2_hard_v8g__ring_ag_71d2c363c67b-_c25c1029v2
docker run --rm --name codex-ring-grt-1029 --cpus=8 --memory=32g --memory-swap=32g -v "$K":/work -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm_grt.log 2>&1 || exit 9
 python3 -I /work/kit_modes.py check /work --step grt --session "tc bc" --hold-repair > /work/kit_modes_grt.log 2>&1 || exit 9
 make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 grt HOLD_SLACK_MARGIN=0 > /work/grt_resume.log 2>&1
 rc=$?
 chown -R "$HUID:$HGID" /work
 exit $rc
'
