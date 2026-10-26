#!/bin/bash
# TOK-DS 10-24: negative control for the fc31 per-layer cut replay. Usage: mutant_fc31.sh <worktree> <run dir> LAYER CUT MUTANT [TAG]
# MUTANT = dv_cut_replay --mutant spec (e.g. shift-kind:CTL:1, corrupt:<link>). Same programme/die/binary as layers_fc31.sh;
# the TB (DV_SLICE mismatches/fault_cycles) and dv_cut_replay check must FAIL (= CAUGHT). Never builds.
set -u
T=$(realpath $1); W=$(realpath $2); Y=$3; C=$4; M=$5; TAG=${6:-m1}; S=/srv/opentallas-scratch/claude
D=$W/mut_$TAG/$Y/$C; DIE=$W/tree_fc31/results/arch/s81_dv_1016/bind9/die.v.gz
[ -x $W/cuts/out_$C/obj/sim ] || { echo "MUTANT fc31 $Y $C NOT RUN: missing binary"; exit 3; }
rm -rf $D; mkdir -p $D
export OT_S81_SELECTED_DEFINES=DSFD_PQ_STATIC_X2,S81CTRL_SRAM_FIFO,S81CTRL_SRAM_P192,S81CTRL_NATIVE32,OT_COLL_NATIVE32,OT_COLL_NATIVE32_OFF,OT_S81ENG_TAP_N32R2,OT_S81SL_KV_TRANSPORT,OT_SVC_ALLQ,SU_SMU_T,SVCQ_ENG_FG3
export OT_S81_SELECTED_SOURCE_ROOT=$S/stw-s81d-tok/layers/root30 OT_SVC_ALLQ=1
cd $T
python3 tools/s81_dv/dv_cut_replay.py gen --die-v $DIE --prog $W/layers_fc31/prog_${Y}_su --cut $W/cuts/$C --out $D --mutant "$M" > $D/gen.log 2>&1 \
  || { echo "MUTANT fc31 $Y $C gen refused: $(tail -1 $D/gen.log)"; exit 4; }
N=$(python3 -c "import json;print(json.load(open('$D/replay.json'))['ncyc'])")
OBJ=$W/cuts/out_$C/obj J=1 bash tools/s81_dv/run_dv_slice.sh $W/cuts/K_$C $D/run +IN=$D/in.txt +OUT=$D/out.txt +TRACE=$D/run/trace.txt +NCYC=$N > $D/sim.log 2>&1; S1=$?
python3 tools/s81_dv/dv_cut_replay.py check --replay $D --run $D/run --out $D/check.json > $D/check.log 2>&1; S2=$?
TB=$(grep -h '^DV_SLICE ' $D/sim.log | tail -1)
V=CAUGHT; [ $S1 = 0 ] && [ $S2 = 0 ] && V=MISSED
echo "MUTANT fc31 $Y $C $M sim_rc $S1 check_rc $S2 -> $V | $TB"
