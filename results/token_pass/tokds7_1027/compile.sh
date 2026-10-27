#!/bin/bash
# TOK-DS-7: compile every S81 layer type on main 262d07038 + codex ds-compiler e4267efa3 (91715602d1), tree_fc31 vehicle, 877 strict-bound define set.
# compile.sh <fixdir> <out> [OT_IDX_SHARD_DIE] LAYER...
set -u
W=/srv/opentallas-scratch2/claude/wt/tok-ds-7-1027
F=$1; O=$2; SD=$3; shift 3
[ "$SD" = - ] || export OT_IDX_SHARD_DIE=$SD
export OT_S81_SELECTED_DEFINES=DSFD_PQ_STATIC_X2,S81CTRL_SRAM_FIFO,S81CTRL_SRAM_P192,S81CTRL_NATIVE32,OT_COLL_NATIVE32,OT_COLL_NATIVE32_OFF,OT_S81ENG_TAP_N32R2,OT_S81SL_KV_TRANSPORT,OT_SVC_ALLQ,SU_SMU_T,OT_ATTN_HCORE,OT_S81ENG_RR_N32,OT_S81C_HCORE_CTLA,OT_S81C_HCORE_RST_TIMED
export OT_S81_SELECTED_SOURCE_ROOT=$W OT_SVC_ALLQ=1
export OT_S81_SELECTED_ASBUILT_MANIFEST=physical/die_plan/s81/bind/asbuilt_b178_coll.json
export OT_S81_SELECTED_CHILD_FILES=rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv,rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv
rm -rf "$O"; mkdir -p "$O"; git -C "$W" rev-parse HEAD > "$O/source_sha.txt"; git -C "$W" status --short -- tools rtl > "$O/source_dirty.txt"
bash "$W/tools/s81_dv/tokfunc/compile_layers.sh" "$W" /srv/opentallas-scratch2/claude/tok-ds-dskr/veh/tree_fc31 "$F" "$O" "$@"
for f in "$O"/cc_*.log; do echo "== $f"; tail -n 3 "$f"; done
echo COMPILE_DONE
