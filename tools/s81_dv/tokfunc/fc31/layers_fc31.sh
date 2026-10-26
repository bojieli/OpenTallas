#!/bin/bash
# TOK-DS 10-24: per-layer replay on the fc31 cuts (prep_fc31.sh + compile_fc31.sh). Usage: layers_fc31.sh <worktree> <run dir> LAYER [TAG]
# Env CUTS (default all four). Consumes built cut binaries <run>/cuts/out_<cut>/obj/sim (never builds: refuses if missing).
# Check uses main dv_cut_replay; OT_S81_XRT_RUNTIME_PROOF (a PASS_CUT_COMPONENT entry_replay.json) is passed through if set.
set -u
T=$(realpath $1); W=$(realpath $2); Y=$3; TAG=${4:-r1}; S=/srv/opentallas-scratch/claude
C=$W/cuts; O=$W/run_$TAG/$Y; CUTS=${CUTS:-cut_0S cut_0N cut_7 cut_3S_ctl}
for c in $CUTS; do [ -x $C/out_$c/obj/sim ] || { echo "LAYER fc31 $Y NOT RUN: missing $C/out_$c/obj/sim"; exit 3; }
  [ -f $C/$c/slice_ports.json ] && [ -f $C/K_$c/kit.json ] || { echo "LAYER fc31 $Y NOT RUN: missing cut/kit $c"; exit 3; }; done
rm -rf $O; mkdir -p $O/builds
for c in $CUTS; do mkdir -p $O/builds/$c; ln -sfn $C/out_$c/obj $O/builds/$c/obj; done
export OT_S81_SELECTED_DEFINES=DSFD_PQ_STATIC_X2,S81CTRL_SRAM_FIFO,S81CTRL_SRAM_P192,S81CTRL_NATIVE32,OT_COLL_NATIVE32,OT_COLL_NATIVE32_OFF,OT_S81ENG_TAP_N32R2,OT_S81SL_KV_TRANSPORT,OT_SVC_ALLQ,SU_SMU_T,SVCQ_ENG_FG3
export OT_S81_SELECTED_SOURCE_ROOT=$S/stw-s81d-tok/layers/root30 OT_SVC_ALLQ=1
cd $T && CUTS="$CUTS" CUT_ROOT=$W KIT_ROOT=$C PROG_ROOT=$W/layers_fc31 DIE_V=$W/tree_fc31/results/arch/s81_dv_1016/bind9/die.v.gz J=1 \
  python3 tools/s81_dv/tokfunc/run_layers.py $T $W/tree_fc31 $S/stw-s81d-tok/layers/fix $O $Y > $O/run_layers.log 2>&1
echo "LAYER fc31 $Y rc $? report $O/layers_report.json"
