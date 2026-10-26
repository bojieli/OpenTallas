#!/bin/bash
# TOK-DS PROG 10-26: L14 with the current compiler (claude/tok-ds-prog-0105) on tree_fc31 + the fc31 legacy selected
# source (root30 s81_dv copy, XRT cfc3feb9, SVCQ_ENG_FG3) -- the 877 source is BLOCKED by xr_timing (XRT d09cf3f6 unqualified).
set -u
W=/srv/opentallas-scratch2/claude/wt/tok-ds-prog-0105; P=/srv/opentallas-scratch2/claude/tok-ds/s81_877/l14_prog
export OT_S81_SELECTED_DEFINES=DSFD_PQ_STATIC_X2,S81CTRL_SRAM_FIFO,S81CTRL_SRAM_P192,S81CTRL_NATIVE32,OT_COLL_NATIVE32,OT_COLL_NATIVE32_OFF,OT_S81ENG_TAP_N32R2,OT_S81SL_KV_TRANSPORT,OT_SVC_ALLQ,SU_SMU_T,SVCQ_ENG_FG3
export OT_S81_SELECTED_SOURCE_ROOT=$P/root30_legacy OT_SVC_ALLQ=1
rm -rf $P/layers_legacy
bash $W/tools/s81_dv/tokfunc/compile_layers.sh $W /srv/opentallas-scratch2/claude/tok-ds-dskr/veh/tree_fc31 $P/fix $P/layers_legacy L14
echo COMPILE_DONE
