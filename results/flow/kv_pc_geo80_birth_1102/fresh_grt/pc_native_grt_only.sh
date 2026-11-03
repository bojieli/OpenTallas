#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-pc-geo80-birth-1102/grt_only
DK=docker; docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name codex-pc-protected-fresh-grt-1102 --cpus=8 --memory=32g --memory-swap=32g -v "$D":/work -w /OpenROAD-flow-scripts/flow sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
export OT_PG_STRICT=1
unset OT_MAXWIRE_UM OT_TAP_GRT_MODE
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1
python3 -I /work/patch_entry.py /OpenROAD-flow-scripts/flow/scripts/global_route.tcl
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-5_1_grt CORNER=TC "CORNERS=tc bc" SKIP_INCREMENTAL_REPAIR=1 SKIP_ANTENNA_REPAIR=1 RECOVER_POWER=0 OPT_POST_GRT_WNS=1 GENERATE_ARTIFACTS_ON_FAILURE=0
' > "$D/fresh_grt.log" 2>&1
$DK run --rm -v "$D":/work sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 chown -R "$(id -u):$(id -g)" /work
test -s "$D/FRESH_GRT_NATIVE_CLEANUP_PASS"
python3 "$D/clk_geom_diff.py" "$D/ORIGINAL.clock.tsv" "$D/reload_post_grt.clock.tsv" --json "$D/original_to_grt.clock_diff.json"
# Independent fresh interpreter reopens the saved output with no module or mutator.
$DK run --rm --name codex-pc-fresh-grt-saved-read-1102 --cpus=1 --memory=4g --memory-swap=4g -v "$D":/work -w /OpenROAD-flow-scripts/flow sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/orfs_hold_mm.py scripts /work/orfs_hold_mm.tcl > /work/read_mm.log 2>&1
make -f Makefile -f /work/audit_only.mk DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=1 ot_private_saved_pg_audit
' > "$D/saved_pg_read.log" 2>&1
$DK run --rm -v "$D":/work sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 chown -R "$(id -u):$(id -g)" /work
grep -q 'INDEPENDENT_SAVED_GRT_PG_PASS' "$D/saved_pg_read.log"
printf '%s\n' 'DPL_DATA_GRT_COMPLETE_REOPENED_PG_PASS_NOT_SIGNED' > "$D/RESULT"
