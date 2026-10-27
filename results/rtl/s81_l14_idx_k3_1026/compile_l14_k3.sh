#!/bin/bash
# TOK-DS-6: L14 compile (rank-3 fixture) at SHARD_K=3, shard die $1 (OT_IDX_SHARD_DIE), same profile as TOK-DS-4.
set -euo pipefail
W=/srv/opentallas-scratch2/claude/wt/tok-ds-6-1026
O=/srv/opentallas-scratch2/claude/tok-ds-6-1026/compile_l14_d$1
export OT_IDX_SHARD_DIE=$1
export OT_S81_SELECTED_DEFINES=DSFD_PQ_STATIC_X2,S81CTRL_SRAM_FIFO,S81CTRL_SRAM_P192,S81CTRL_NATIVE32,OT_COLL_NATIVE32,OT_COLL_NATIVE32_OFF,OT_S81ENG_TAP_N32R2,OT_S81SL_KV_TRANSPORT,OT_SVC_ALLQ,SU_SMU_T,OT_ATTN_HCORE,OT_S81ENG_RR_N32,OT_S81C_HCORE_CTLA,OT_S81C_HCORE_RST_TIMED
export OT_S81_SELECTED_SOURCE_ROOT=$W OT_SVC_ALLQ=1
export OT_S81_SELECTED_ASBUILT_MANIFEST=physical/die_plan/s81/bind/asbuilt_b178_coll.json
export OT_S81_SELECTED_CHILD_FILES=rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv,rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv
rm -rf "$O"; mkdir -p "$O"; git -C "$W" rev-parse HEAD > "$O/source_sha.txt"; git -C "$W" status --short -- tools rtl > "$O/source_dirty.txt"
bash "$W/tools/s81_dv/tokfunc/compile_layers.sh" "$W" /srv/opentallas-scratch2/claude/tok-ds-dskr/veh/tree_fc31 /srv/opentallas-scratch2/claude/tok-ds/s81_877/l14_prog/fix_r3 "$O" L14
cat "$O/cc_L14_su.log"
