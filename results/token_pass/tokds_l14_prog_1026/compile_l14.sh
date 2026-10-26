#!/bin/bash
# TOK-DS PROG 10-26: compile L14 (single user) with the current compiler (claude/tok-ds-prog-0105 worktree) on tree_fc31,
# selected defines + source root = the strict-bound 877 cohort (no FG3).
set -u
W=/srv/opentallas-scratch2/claude/wt/tok-ds-prog-0105
export OT_S81_SELECTED_DEFINES=DSFD_PQ_STATIC_X2,S81CTRL_SRAM_FIFO,S81CTRL_SRAM_P192,S81CTRL_NATIVE32,OT_COLL_NATIVE32,OT_COLL_NATIVE32_OFF,OT_S81ENG_TAP_N32R2,OT_S81SL_KV_TRANSPORT,OT_SVC_ALLQ,SU_SMU_T,OT_ATTN_HCORE,OT_S81ENG_RR_N32,OT_S81C_HCORE_CTLA,OT_S81C_HCORE_RST_TIMED
export OT_S81_SELECTED_SOURCE_ROOT=$W OT_SVC_ALLQ=1
rm -rf /srv/opentallas-scratch2/claude/tok-ds/s81_877/l14_prog/layers
bash $W/tools/s81_dv/tokfunc/compile_layers.sh $W /srv/opentallas-scratch2/claude/tok-ds-dskr/veh/tree_fc31 /srv/opentallas-scratch2/claude/tok-ds/s81_877/l14_prog/fix /srv/opentallas-scratch2/claude/tok-ds/s81_877/l14_prog/layers L14
echo COMPILE_DONE
