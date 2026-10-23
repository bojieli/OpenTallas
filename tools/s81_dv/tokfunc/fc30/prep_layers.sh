#!/bin/bash
set -u
L=/srv/opentallas-scratch/claude/stw-s81d-tok/layers; R=/srv/opentallas-scratch/claude/stw-s81d-tok/layers/root30; T=/srv/opentallas-scratch/claude/stw-s81d-tok/layers/tree_fc30
export OT_S81_SELECTED_DEFINES=DSFD_PQ_STATIC_X2,S81CTRL_SRAM_FIFO,S81CTRL_SRAM_P192,S81CTRL_NATIVE32,OT_COLL_NATIVE32,OT_COLL_NATIVE32_OFF,OT_S81ENG_TAP_N32R2,OT_S81SL_KV_TRANSPORT,OT_SVC_ALLQ,SU_SMU_T,SVCQ_ENG_FG3
export OT_S81_SELECTED_SOURCE_ROOT=$R OT_SVC_ALLQ=1
cd $R
rm -rf $T; python3 tools/s81_dv/tokfunc/mk_tree.py --die-v /srv/opentallas-scratch/claude/stw-s81d-tok/fc30/bind/bind/die.v --plan /srv/opentallas-scratch/claude/stw-s81c-cap30/gen-main/plan.json --land /srv/opentallas-scratch/claude/stw-s81c-cap30/gen-main/land.json --out $T --tag fc30 > $L/mk_tree.log 2>&1; echo "MK_TREE rc $? $(cat $L/mk_tree.log)"
rm -rf $L/layers_fc30; bash tools/s81_dv/tokfunc/compile_layers.sh $R $T $L/fix $L/layers_fc30 L0 L2 L14 L20
echo PREP_DONE
