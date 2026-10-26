#!/bin/bash
# TOK-DS 10-24 (COORD 18:55 sink canonical): recompile L0/L2/L14/L20 on tree_fc31 with the sink-aware compiler (verify_sink tree),
# prepare native split-control programmes, replay on the BK-sink fc31 cut_3S_ctl WITHOUT --bk-drain-sink (canonical expectations).
#   usage: canon_layers.sh <src tree> <work dir> [LAYERS]
set -u
T=$(realpath $1); W=$(realpath -m $2); LAYS=${3:-"L0 L2 L14 L20"}
S=/srv/opentallas-scratch/claude; B=$S/codex-s81; C=$HOME/s81p10/fc31; K=$B/bk_drain_layer/kit; OBJ=$B/bk_drain_layer/out/obj
mkdir -p $W; [ -e $W/tree_fc31 ] || ln -s $S/tok-ds/fc31/tree_fc31 $W/tree_fc31
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
if [ ! -f $W/compile.done ]; then
  bash $T/tools/s81_dv/tokfunc/fc31/compile_fc31.sh $T $W > $W/compile.log 2>&1; touch $W/compile.done
fi
export OT_S81_SELECTED_DEFINES=DSFD_PQ_STATIC_X2,S81CTRL_SRAM_FIFO,S81CTRL_SRAM_P192,S81CTRL_NATIVE32,OT_COLL_NATIVE32,OT_COLL_NATIVE32_OFF,OT_S81ENG_TAP_N32R2,OT_S81SL_KV_TRANSPORT,OT_SVC_ALLQ,SU_SMU_T,SVCQ_ENG_FG3
export OT_S81_SELECTED_SOURCE_ROOT=$B/src OT_SVC_ALLQ=1
I=$S/tok-ds/bk2/idle2000
[ -f $I/trace.txt ] || I=$S/tok-ds/bk/idle2000
for Y in $LAYS; do (
  F=$HOME/s81p10/old/intel2/stw-s81d-tok.ep5/layers/fix/$Y/meta.json; P=$W/ctl_$Y
  rm -rf $P; cd $T && python3 tools/s81_dv/tokfunc/prepare_split_control.py --tree $C/tree_fc31 --program $W/layers_fc31/prog_${Y}_su --fixture-meta $F --out $P > $W/prepare_$Y.log 2>&1 || { echo "CANON $Y prepare FAIL"; exit 1; }
  rm -rf $W/replay_$Y
  python3 tools/s81_dv/tokfunc/run_entry_replay.py --src $T --die-v $C/tree_fc31/results/arch/s81_dv_1016/bind9/die.v.gz \
    --cut $C/cuts/cut_3S_ctl --kit $K --obj $OBJ --idle-run $I --progs $P --fixture-meta $F --ks-user 0 --out $W/replay_$Y \
    --par 3 --jobs 0 1 --mutant 1:corrupt:hf_7N_l0:33 --ks ${KS:-3093} > $W/replay_$Y.log 2>&1
  echo "CANON $Y rc $? $(grep ENTRY_REPLAY $W/replay_$Y.log | tail -1)" ) &
done; wait; echo CANON_LAYERS_DONE
