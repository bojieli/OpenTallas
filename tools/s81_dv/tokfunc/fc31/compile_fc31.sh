#!/bin/bash
# TOK-DS 10-24: compile L0/L2/L14/L20 single-user layer programmes on the fc31 die tree (main compiler), checkpoint fixtures
# verified against results/rtl/s81_layer_tput_1018/fixtures/*.sha256.json. Selected source root = the bind's root30 (as fc30).
set -u
T=$(realpath $1); W=$(realpath $2); S=/srv/opentallas-scratch/claude
export OT_S81_SELECTED_DEFINES=DSFD_PQ_STATIC_X2,S81CTRL_SRAM_FIFO,S81CTRL_SRAM_P192,S81CTRL_NATIVE32,OT_COLL_NATIVE32,OT_COLL_NATIVE32_OFF,OT_S81ENG_TAP_N32R2,OT_S81SL_KV_TRANSPORT,OT_SVC_ALLQ,SU_SMU_T,SVCQ_ENG_FG3
export OT_S81_SELECTED_SOURCE_ROOT=$S/stw-s81d-tok/layers/root30 OT_SVC_ALLQ=1
rm -rf $W/layers_fc31
bash $T/tools/s81_dv/tokfunc/compile_layers.sh $T $W/tree_fc31 $S/stw-s81d-tok/layers/fix $W/layers_fc31 L0 L2 L14 L20
echo COMPILE_DONE
