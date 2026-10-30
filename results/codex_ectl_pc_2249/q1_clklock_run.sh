#!/bin/bash
set -uo pipefail
D=/srv/opentallas-scratch2/claude/codex-ectl-pc-2249/q1_w243s_clklock
rc=0
docker run --rm --name codex-ectl-q1-clklock2249 --cpus=12 --memory=32g --memory-swap=32g -v "$D":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm_clklock.log 2>&1 || exit 9; M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=12"; $M grt && $M route && $M do-finish' > "$D/run_clklock.log" 2>&1 || rc=$?
docker run --rm -v "$D":/work openroad/orfs:asap7lock chown -R 1000:1000 /work
if [ "$rc" = 0 ]; then bash "$D/run_kit_kv.sh" "$D" post 32 12; rc=$?; fi
echo "CLKLOCK_RC $rc" >> "$D/run_clklock.log"
exit "$rc"
