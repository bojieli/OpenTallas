#!/bin/bash
# TOK-DS 2026-10-26: L14 single-user compile from a FULL checkout of claude/tok-ds-cmp-1026@52e5e662a,
# same selected profile as Codex xrt-l14-1026/compile_manifest.sh (02:28), to separate sparse-tree
# receipt artifacts (missing bench check.json) from real lowering GAPs.  Diagnostic compile only.
set -euo pipefail
W=/srv/opentallas-scratch2/claude/wt/tok-ds-l14cc-1026
O=/srv/opentallas-scratch2/claude/tok-ds/s81_877/l14_cc_cmp_52e5_bound
export OT_S81_SELECTED_DEFINES=DSFD_PQ_STATIC_X2,S81CTRL_SRAM_FIFO,S81CTRL_SRAM_P192,S81CTRL_NATIVE32,OT_COLL_NATIVE32,OT_COLL_NATIVE32_OFF,OT_S81ENG_TAP_N32R2,OT_S81SL_KV_TRANSPORT,OT_SVC_ALLQ,SU_SMU_T,OT_ATTN_HCORE,OT_S81ENG_RR_N32,OT_S81C_HCORE_CTLA,OT_S81C_HCORE_RST_TIMED
export OT_S81_SELECTED_SOURCE_ROOT=$W OT_SVC_ALLQ=1
export OT_S81_SELECTED_ASBUILT_MANIFEST=physical/die_plan/s81/bind/asbuilt_b178_coll.json
export OT_S81_SELECTED_CHILD_FILES=rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv,rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv
export OT_SVC_BOUND_ROUTES=$W/results/token_pass/bound_die_1026/svc_routes.json
mkdir -p "$O"; git -C "$W" rev-parse HEAD > "$O/source_sha.txt"
bash "$W/tools/s81_dv/tokfunc/compile_layers.sh" "$W" /srv/opentallas-scratch2/claude/tok-ds-dskr/veh/tree_fc31 /srv/opentallas-scratch2/claude/tok-ds/s81_877/l14_prog/fix "$O" L14
cat "$O/cc_L14_su.log"
test -s "$O/prog_L14_su/schedule.json"
