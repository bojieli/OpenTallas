#!/bin/bash
# same as compile_l14_legacy.sh but --slice s_6S (the carve frames fE2_p1/p4_b0 = u_f_6R01/u_f_6R1x are column 6)
set -u
W=/srv/opentallas-scratch2/claude/wt/tok-ds-prog-0105; P=/srv/opentallas-scratch2/claude/tok-ds/s81_877/l14_prog
export OT_S81_SELECTED_DEFINES=DSFD_PQ_STATIC_X2,S81CTRL_SRAM_FIFO,S81CTRL_SRAM_P192,S81CTRL_NATIVE32,OT_COLL_NATIVE32,OT_COLL_NATIVE32_OFF,OT_S81ENG_TAP_N32R2,OT_S81SL_KV_TRANSPORT,OT_SVC_ALLQ,SU_SMU_T,SVCQ_ENG_FG3
export OT_S81_SELECTED_SOURCE_ROOT=$P/root30_legacy OT_SVC_ALLQ=1 OT_XS_FRAME_SCHEDULE_DIR=$P/layers_legacy/frame_schedules
rm -rf $P/layers_legacy_s6S; mkdir -p $P/layers_legacy_s6S; cd $W
/usr/bin/time -v -o $P/layers_legacy_s6S/cc.time python3 tools/s81_dv/dv_layer_compile.py --layer L14 --slice s_6S --out $P/layers_legacy_s6S/prog_L14_su --die-src /srv/opentallas-scratch2/claude/tok-ds-dskr/veh/tree_fc31 --fixtures $P/fix/L14 > $P/layers_legacy_s6S/cc.log 2> $P/layers_legacy_s6S/cc.err
echo CC rc $?
