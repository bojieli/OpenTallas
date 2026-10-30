#!/bin/bash
set -uo pipefail
D=/srv/opentallas-scratch2/claude/codex-ectl-1030/pv_pad_proto4
. "$D/variant.env"
rc=0
docker run --rm --name codex-pv-pad-1030 --cpus=12 --memory=40g --memory-swap=40g -v "$D":/work -e OT_MAX_FANOUT="$OT_MAX_FANOUT" -e OT_SLEW_MARGIN="$OT_SLEW_MARGIN" -e OT_SETUP_MARGIN="$OT_SETUP_MARGIN" -e OT_HOLD_MARGIN="$OT_HOLD_MARGIN" -e OT_HOLD_ALLOW_SETUP="$OT_HOLD_ALLOW_SETUP" -e OT_HOLD_MAXBUF="$OT_HOLD_MAXBUF" -e OT_PRD_PASS=1 -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm_pvpad.log 2>&1 || exit 9; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=12 do-grt CORNER=TC CORNERS="tc BC" SKIP_INCREMENTAL_REPAIR=1' > "$D/prototype.log" 2>&1 || rc=$?
docker run --rm -v "$D":/work openroad/orfs:asap7lock chown -R 1000:1000 /work
printf 'PV_PAD_PROTO_RC %s\n' "$rc" >> "$D/prototype.log"
exit "$rc"
