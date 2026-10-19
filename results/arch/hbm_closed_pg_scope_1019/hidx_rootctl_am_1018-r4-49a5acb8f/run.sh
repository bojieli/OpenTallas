#!/bin/bash
set -u
sha256sum /srv/opentallas-scratch/claude/closure-loop/hidx_rootctl_am_1018-r4-49a5acb8f/routes/hidx_rootctl_am_1018_r4_49a5acb8f/work/orfs/results/asap7/opentallas_ot_hbm_idx_rootctl_static_am_asap7_ref_hidx_rootctl_am_1018_r4_49a5acb8f/base/6_final.odb > odb.before.sha256
sha256sum ../native_pg_binding.tcl ../audit_native_pg.tcl > helper.sha256
docker run --rm --network none -v /srv/opentallas-scratch/claude/closure-loop/hidx_rootctl_am_1018-r4-49a5acb8f/routes/hidx_rootctl_am_1018_r4_49a5acb8f/work/orfs/results/asap7/opentallas_ot_hbm_idx_rootctl_static_am_asap7_ref_hidx_rootctl_am_1018_r4_49a5acb8f/base/6_final.odb:/input.odb:ro -v "$PWD/..":/proof -e OT_PG_AUDIT_ODB=/input.odb -e OT_PG_AUDIT_REPORT=/proof/hidx_rootctl_am_1018-r4-49a5acb8f/report.tcldict --entrypoint /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 -exit /proof/audit_native_pg.tcl > audit.log 2>&1
rc=$?
sha256sum /srv/opentallas-scratch/claude/closure-loop/hidx_rootctl_am_1018-r4-49a5acb8f/routes/hidx_rootctl_am_1018_r4_49a5acb8f/work/orfs/results/asap7/opentallas_ot_hbm_idx_rootctl_static_am_asap7_ref_hidx_rootctl_am_1018_r4_49a5acb8f/base/6_final.odb > odb.after.sha256
printf '%s\n' "$rc" > audit.rc
cmp odb.before.sha256 odb.after.sha256 || exit 97
exit "$rc"
