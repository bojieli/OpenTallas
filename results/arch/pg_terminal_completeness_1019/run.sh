#!/bin/bash
set -euo pipefail
image=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
route=/srv/opentallas-scratch/claude/closure-loop/hdie_col_idx256_1019-fan32g1-2727e1f68/routes/hdie_col_idx256_1019_fan32g1_2727e1f68
run() { docker run --rm --entrypoint bash -v "$PWD:/proof" -v "$route:/route:ro" "$image" -lc "$1"; }
or=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad
run "$or -exit /proof/prove.tcl" > prove.log 2>&1
run "$or -exit /proof/domains.tcl" > domains.log 2>&1
original=/route/work/orfs/results/asap7/opentallas_ot_hbm_static_cfg_collar_idx256_asap7_ref_hdie_col_idx256_1019_fan32g1_2727e1f68/base/6_final.odb
set +e
run "OT_PG_AUDIT_ODB=$original OT_PG_AUDIT_REPORT=/proof/audit.original.tcldict $or -exit /proof/audit_native_pg.tcl" > audit.original.log 2>&1
rc=$?
set -e
[ "$rc" = 2 ]
sha256sum audit.original.tcldict > existing.before.sha256
set +e
run "OT_PG_AUDIT_ODB=/proof/source_order_clone.odb OT_PG_AUDIT_REPORT=/proof/audit.original.tcldict $or -exit /proof/audit_native_pg.tcl" > audit.overwrite.log 2>&1
rc=$?
set -e
[ "$rc" = 3 ]
sha256sum -c existing.before.sha256 > preserve.log
run "OT_PG_AUDIT_ODB=/proof/source_order_clone.odb OT_PG_AUDIT_REPORT=/proof/audit.clone.tcldict $or -exit /proof/audit_native_pg.tcl" > audit.clone.log 2>&1
sha256sum source_order_clone.odb > clone.sha256
cat prove.log domains.log audit.original.log audit.overwrite.log preserve.log audit.clone.log clone.sha256
