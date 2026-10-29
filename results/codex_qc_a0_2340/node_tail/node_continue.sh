#!/bin/bash
set -euo pipefail
K=/srv/opentallas-scratch2/claude/codex-qc-a0-2340/node_finalff
# Exact reviewed and NUMBER-qualified GRT checkpoint; no synthesis, CTS, or GRT repeated.
docker run --rm --name codex-qca0-node-drt-continue --cpus=8 --memory=32g --memory-swap=32g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl
M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 CORNER=TC CORNERS=tc\ BC OT_HOLD_MM=1 OT_MM_SETUP_CORNER=tc"
# Array preserves the two-corner string as one make argument.
M=(make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 CORNER=TC "CORNERS=tc BC" OT_HOLD_MM=1 OT_MM_SETUP_CORNER=tc)
rc=0
"${M[@]}" do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc && "${M[@]}" do-finish do-generate_abstract || rc=$?
chown -R 1000:1000 /work
exit $rc' > "$K/drt_continue.log" 2>&1
SIGNOFF_DOCKER=docker python3 -I "$K/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --out "$K/signoff" --image openroad/orfs:asap7lock > "$K/signoff.log" 2>&1
