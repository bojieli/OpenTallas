#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-pc-geo80-birth-1102/drt_only
IMAGE=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
DK=docker;docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name codex-pc-observational-drt-1102 --cpus=8 --memory=32g --memory-swap=32g -v "$D":/work -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
export OT_PG_STRICT=1
python3 -I /work/orfs_hold_mm.py scripts /work/orfs_hold_mm.tcl >/work/drt_mm.log 2>&1
python3 -I /work/patch_private_drt.py scripts --packet /work
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-5_2_route CORNER=TC "CORNERS=tc bc"
' > "$D/route_only.log" 2>&1
$DK run --rm -v "$D":/work "$IMAGE" chown -R "$(id -u):$(id -g)" /work
grep -q 'PC_DRT_OBSERVATIONAL_NO_BIRTH_COMPLETE active=0' "$D/route_only.log"
B=run/results/asap7/hc_qkd_kvs_pc__397_44x362_88/base
$DK run --rm --memory=16g --memory-swap=16g --cpus=2 -v "$D":/work -e OT_DB=/work/$B/5_2_route.odb -e OT_OUT=/work/route_only.clock.tsv -e OT_TAG=post:5_2_route.odb -e OT_NETS=/work/$B/clk_freeze_nets.txt "$IMAGE" bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /work/clk_dump_db.tcl' > "$D/route_clock_read.log" 2>&1
$DK run --rm -v "$D":/work "$IMAGE" chown -R "$(id -u):$(id -g)" /work
python3 "$D/clk_geom_diff.py" "$D/ORIGINAL.clock.tsv" "$D/route_only.clock.tsv" --json "$D/original_to_route.clock_diff.json"
# Independent fresh saved-route PG audit; no module/connect/repair/STA.
$DK run --rm --cpus=1 --memory=4g --memory-swap=4g -v "$D":/work -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/orfs_hold_mm.py scripts /work/orfs_hold_mm.tcl >/work/route_read_mm.log 2>&1
make -f Makefile -f /work/audit_only.mk DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=1 ot_private_saved_pg_audit
' > "$D/saved_route_pg_read.log" 2>&1
$DK run --rm -v "$D":/work "$IMAGE" chown -R "$(id -u):$(id -g)" /work
grep -q 'INDEPENDENT_SAVED_ROUTE_PG_PASS' "$D/saved_route_pg_read.log"
printf '%s\n' 'OBSERVATIONAL_DRT_COMPLETE_CLOCK_AND_REOPENED_PG_PASS_NOT_SIGNED' > "$D/RESULT"
