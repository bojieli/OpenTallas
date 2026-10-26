#!/bin/bash
# STW-S81d-TOK: per-layer replay on the cap30-framecal cuts (die.v 3b4b975d). Usage: layers_fc30.sh LAYER (L0|L2|L14|L20)
# Consumes the built cut binaries fc30/cuts/out_<cut>/obj/sim (never builds: refuses if one is missing).
P=/srv/opentallas-scratch/claude/stw-s81d-tok/layers; C=/srv/opentallas-scratch/claude/stw-s81d-tok/fc30/cuts; Y=$1; O=$P/run_fc30/$Y
CUTS="cut_0S cut_0N cut_7 cut_3S_ctl"
for c in $CUTS; do [ -x $C/out_$c/obj/sim ] || { echo "LAYER fc30 $Y NOT RUN: missing $C/out_$c/obj/sim on $(hostname)"; exit 3; }
  [ -f $C/$c/slice_ports.json ] && [ -f $C/K_$c/kit.json ] || { echo "LAYER fc30 $Y NOT RUN: missing cut/kit $c"; exit 3; }; done
rm -rf $O; mkdir -p $O/builds $P/cutroot_fc30/cuts
for c in $CUTS; do ln -sfn $C/$c $P/cutroot_fc30/cuts/$c; mkdir -p $O/builds/$c; ln -sfn $C/out_$c/obj $O/builds/$c/obj; done
export OT_S81_SELECTED_DEFINES=DSFD_PQ_STATIC_X2,S81CTRL_SRAM_FIFO,S81CTRL_SRAM_P192,S81CTRL_NATIVE32,OT_COLL_NATIVE32,OT_COLL_NATIVE32_OFF,OT_S81ENG_TAP_N32R2,OT_S81SL_KV_TRANSPORT,OT_SVC_ALLQ,SU_SMU_T,SVCQ_ENG_FG3 OT_SVC_ALLQ=1
cd $P/root30 && CUTS="$CUTS" CUT_ROOT=$P/cutroot_fc30 KIT_ROOT=$C PROG_ROOT=$P/layers_fc30 OT_S81_SELECTED_SOURCE_ROOT=$P/root30 \
  python3 tools/s81_dv/tokfunc/run_layers.py $P/root30 $P/tree_fc30 $P/fix $O $Y > $O/run_layers.log 2>&1
echo "LAYER fc30 $Y rc $? report $O/layers_report.json"
