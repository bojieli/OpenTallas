#!/bin/bash
set -uo pipefail
D=/srv/opentallas-scratch2/claude/codex-ectl-1030/pc_leaf64
rc=0
docker run --rm --name codex-pcleaf64-1030 --cpus=12 --memory=40g --memory-swap=40g -v "$D":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm_uniform.log 2>&1 || exit 9; M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=12"; $M do-cts && $M do-grt' > "$D/prototype.log" 2>&1 || rc=$?
docker run --rm -v "$D":/work openroad/orfs:asap7lock chown -R 1000:1000 /work
printf 'PC_UNIFORM_PROTO_RC %s\n' "$rc" >> "$D/prototype.log"
exit "$rc"
