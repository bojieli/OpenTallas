#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-pc-geo80-birth-1102/grt_only
DK=docker; docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name codex-pc-protected-fresh-grt-1102 --cpus=8 --memory=32g --memory-swap=32g -v "$D":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
export OT_PG_STRICT=1
unset OT_MAXWIRE_UM OT_TAP_GRT_MODE
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1
python3 -I /work/patch_entry.py /OpenROAD-flow-scripts/flow/scripts/global_route.tcl
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-5_1_grt CORNER=TC "CORNERS=tc bc" SKIP_INCREMENTAL_REPAIR=1 SKIP_ANTENNA_REPAIR=1 RECOVER_POWER=0 OPT_POST_GRT_WNS=1 GENERATE_ARTIFACTS_ON_FAILURE=0
' > "$D/fresh_grt.log" 2>&1
$DK run --rm -v "$D":/work openroad/orfs:asap7lock chown -R "$(id -u):$(id -g)" /work
test -s "$D/FRESH_GRT_NATIVE_CLEANUP_PASS"
python3 "$D/clk_geom_diff.py" "$D/ORIGINAL.clock.tsv" "$D/reload_post_grt.clock.tsv" --json "$D/original_to_grt.clock_diff.json"
# A separate fresh saved-ODB PG query is a required gate before any later release.
printf '%s\n' 'DPL_DATA_GRT_COMPLETE_REOPENED_PG_AUDIT_PENDING_NOT_SIGNED' > "$D/RESULT"
