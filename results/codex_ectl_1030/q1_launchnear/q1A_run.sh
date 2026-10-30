#!/bin/bash
set -uo pipefail
D=/srv/opentallas-scratch2/claude/codex-ectl-1030/q1A_grt
rc=0
docker run --rm --name codex-q1A-grt-1030 --cpus=12 --memory=32g --memory-swap=32g -v "$D":/work -e OT_MAX_FANOUT=0 -e OT_SLEW_MARGIN=20 -e OT_SETUP_MARGIN=10 -e OT_HOLD_MARGIN=15 -e OT_HOLD_ALLOW_SETUP=1 -e OT_HOLD_MAXBUF=40 -e OT_PRD_PASS=1 -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm_q1A.log 2>&1 || exit 9; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=12 do-grt CORNER=TC CORNERS="tc BC" SKIP_INCREMENTAL_REPAIR=1' > "$D/prototype.log" 2>&1 || rc=$?
docker run --rm -v "$D":/work openroad/orfs:asap7lock chown -R 1000:1000 /work
printf 'Q1A_PROTO_RC %s\n' "$rc" >> "$D/prototype.log"
exit "$rc"
