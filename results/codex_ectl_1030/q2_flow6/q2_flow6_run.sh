#!/bin/bash
set -uo pipefail
D=/srv/opentallas-scratch2/claude/codex-ectl-1030/q2_flow6
rc=0
docker run --rm --name codex-q2-flow6-1030 --cpus=12 --memory=32g --memory-swap=32g -v "$D":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm_flow6.log 2>&1 || exit 9; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=12 do-grt' > "$D/prototype.log" 2>&1 || rc=$?
docker run --rm -v "$D":/work openroad/orfs:asap7lock chown -R 1000:1000 /work
printf 'Q2_FLOW6_PROTO_RC %s\n' "$rc" >> "$D/prototype.log"
exit "$rc"
