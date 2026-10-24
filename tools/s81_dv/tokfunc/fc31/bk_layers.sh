#!/bin/bash
# TOK-DS 10-24: native split-layer control replay (job0 + job1, prepare_split_control.py programmes) on the fc31 cut_3S_ctl
# rebuilt with the opt-in BK addressed-drain sink (Codex candidate codex/s81-integrate-1024 51ae2e4cef: dsdv_bk_g/ot_dsdv_vstop
# BK_DRAIN_SINK=1, kit epyc3 codex-s81/bk_drain_layer/kit).  Same tools as main (dv_cut_replay/run_entry_replay =
# the c3 tools that gave L0 PASS 49f7915d5a).  Never builds.  Usage: bk_layers.sh <worktree> <out root> LAYER [KS]
set -u
T=$(realpath $1); O=$(realpath -m $2); Y=$3; KS=${4:-3093}
B=/srv/opentallas-scratch/claude/codex-s81; C=$HOME/s81p10/fc31; K=$B/bk_drain_layer/kit; OBJ=$B/bk_drain_layer/out/obj
F=$HOME/s81p10/old/intel2/stw-s81d-tok.ep5/layers/fix/$Y/meta.json; P=$B/layer_control_${Y}_c3
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
export OT_S81_SELECTED_DEFINES=DSFD_PQ_STATIC_X2,S81CTRL_SRAM_FIFO,S81CTRL_SRAM_P192,S81CTRL_NATIVE32,OT_COLL_NATIVE32,OT_COLL_NATIVE32_OFF,OT_S81ENG_TAP_N32R2,OT_S81SL_KV_TRANSPORT,OT_SVC_ALLQ,SU_SMU_T,SVCQ_ENG_FG3
export OT_S81_SELECTED_SOURCE_ROOT=$B/src OT_SVC_ALLQ=1
[ -x $OBJ/sim ] || { echo "BK $Y NOT RUN: no BK binary"; exit 3; }
[ -d $P/replay_job0 ] || { echo "BK $Y NOT RUN: no split programme $P"; exit 3; }
mkdir -p $O
I=$O/idle2000
if [ ! -f $I/trace.txt ]; then mkdir -p $I; OBJ=$OBJ J=1 bash $T/tools/s81_dv/run_dv_slice.sh $K $I +NCYC=2000 +TRACE=$I/trace.txt > $I.log 2>&1; fi
grep -q "fault_cycles=0 " $I/run.log || { echo "BK $Y idle faults: $(grep -h '^DV_SLICE ' $I/run.log)"; exit 4; }
rm -rf $O/$Y
cd $T && python3 tools/s81_dv/tokfunc/run_entry_replay.py --src $T --die-v $C/tree_fc31/results/arch/s81_dv_1016/bind9/die.v.gz \
  --cut $C/cuts/cut_3S_ctl --kit $K --obj $OBJ --idle-run $I --progs $P --fixture-meta $F --ks-user 0 --out $O/$Y \
  --par 3 --jobs 0 1 --mutant 1:corrupt:hf_7N_l0:33 --ks $KS > $O/$Y.log 2>&1
echo "BK $Y rc $? $(grep ENTRY_REPLAY $O/$Y.log | tail -1)"
