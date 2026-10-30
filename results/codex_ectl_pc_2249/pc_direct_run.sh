#!/bin/bash
set -uo pipefail
D=/srv/opentallas-scratch2/claude/codex-ectl-pc-2249/pc_d35q_direct
rc=0
docker run --rm --name codex-ectl-pc-direct2249 --cpus=16 --memory=48g --memory-swap=48g -v "$D":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm_direct.log 2>&1 || exit 9; M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16"; $M cts && $M grt && $M route && $M do-finish' > "$D/run_direct.log" 2>&1 || rc=$?
docker run --rm -v "$D":/work openroad/orfs:asap7lock chown -R 1000:1000 /work
if [ "$rc" = 0 ]; then bash "$D/run_kit_kv.sh" "$D" post 48 16; rc=$?; fi
echo "PC_DIRECT_RC $rc" >> "$D/run_direct.log"
exit "$rc"
