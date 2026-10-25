#!/bin/bash
# TOK-DS-GAPS 10-24: data-cut arithmetic exactness -- the smoke slice's attn xfin NX flit (layer_prog/norm_nx.py) on the
# fc31 data cut that holds it (cut_0S: u_s_0S).  Compiles the layer with --entry-norm-check into a NEW dir, replays the
# existing fc31 cut binary (never builds), checks, then two negative controls:
#   MUT_IN  corrupt:xrW_0S_l0:91  -- flips beat bit 91 of the first word entering the cut on the line = data bit 30 of
#           the first entry target-5 write (H row 0, leaf 0: BF16 exponent MSB of HC copy 0 element 1) -> new sim; the
#           NX flit check must FAIL (input corruption reaches the arithmetic output)
#   MUT_EX  expect-shift:NX:1     -- same trace, every NX check one cycle late -> must FAIL (the cycle is checked)
# Usage: gaps_nx.sh <worktree> <out dir> LAYER [STEPS]   STEPS default "compile base mut_in mut_ex"
set -u
T=$(realpath $1); O=$(realpath -m $2); Y=$3; STEPS=${4:-compile base mut_in mut_ex}
S=/srv/opentallas-scratch/claude; W=$S/tok-ds/fc31
# A cut with forwarded clocks needs the reclocked testbench. Keep the die/program
# source independent of that testbench, so a completed build can be reused.
C=${FC31_DATA_CUTS:-$W/cuts}; CUT=cut_0S
export OT_S81_SELECTED_DEFINES=DSFD_PQ_STATIC_X2,S81CTRL_SRAM_FIFO,S81CTRL_SRAM_P192,S81CTRL_NATIVE32,OT_COLL_NATIVE32,OT_COLL_NATIVE32_OFF,OT_S81ENG_TAP_N32R2,OT_S81SL_KV_TRANSPORT,OT_SVC_ALLQ,SU_SMU_T,SVCQ_ENG_FG3
export OT_S81_SELECTED_SOURCE_ROOT=$S/stw-s81d-tok/layers/root30 OT_SVC_ALLQ=1
export OT_XS_FRAME_SCHEDULE_DIR=$W/layers_fc31/frame_schedules
export OT_S81_XRT_RUNTIME_PROOF=$S/codex-s81/entry_qualified_fc31/entry_replay.json
DIE=$W/tree_fc31/results/arch/s81_dv_1016/bind9/die.v.gz; P=$O/prog_${Y}_su
mkdir -p $O; cd $T
if [[ " $STEPS " == *" compile "* ]]; then
  [ -e $P ] && { echo "GAPS $Y: $P exists (fresh dirs only)"; exit 3; }
  /usr/bin/time -v -o $O/cc_$Y.time python3 tools/s81_dv/dv_layer_compile.py --layer $Y --out $P --die-src $W/tree_fc31 \
    --fixtures $S/stw-s81d-tok/layers/fix/$Y --entry-norm-check > $O/cc_$Y.log 2> $O/cc_$Y.err || { echo "GAPS $Y compile FAIL"; tail -3 $O/cc_$Y.err; exit 1; }
fi
if [[ " $STEPS " == *" base "* || " $STEPS " == *" mut_in "* ]]; then
  [ -x $C/out_$CUT/obj/sim ] || { echo "GAPS $Y NOT RUN: no $C/out_$CUT/obj/sim"; exit 3; }
fi
# t0: the entry beats are at negative layer cycles; the earliest line word must land at bench >= its lane age
T0=$(python3 -c "import json; S=json.load(open('$P/schedule.json')); print(max(100, 100 - min(e['cycle'] for e in S['events'])))")
replay() {  # name mutant(or '') sim(0/1) [trace-of]
  local R=$O/$Y/$CUT/$1
  [ ! -e "$R" ] || { echo "GAPS $Y $1: $R exists (fresh dirs only)"; return 3; }
  mkdir -p $R
  python3 tools/s81_dv/dv_cut_replay.py gen --die-v $DIE --prog $P --cut $C/$CUT --out $R --t0 $T0 ${2:+--mutant $2} > $R/gen.log 2>&1 \
    || { echo "GAPS $Y $1 gen FAIL: $(tail -1 $R/gen.log)"; return 1; }
  local RUN=$R/run
  if [ "$3" = 1 ]; then
    NC=$(python3 -c "import json; print(json.load(open('$R/replay.json'))['ncyc'])")
    OBJ=$C/out_$CUT/obj J=1 bash tools/s81_dv/run_dv_slice.sh $C/K_$CUT $RUN +IN=$R/in.txt +OUT=$R/out.txt \
      +TRACE=$RUN/trace.txt +NCYC=$NC > $R/sim.log 2>&1
  else RUN=$O/$Y/$CUT/$4/run; fi
  python3 tools/s81_dv/dv_cut_replay.py check --replay $R --run $RUN --out $R/check.json > $R/check.log 2>&1
  echo "GAPS $Y $1 t0 $T0: $(grep -h '^DV_SLICE ' $RUN/run.log) | $(tail -1 $R/check.log)"
}
[[ " $STEPS " == *" base "* ]] && replay base "" 1
[[ " $STEPS " == *" mut_in "* ]] && replay mut_in corrupt:xrW_0S_l0:91 1
[[ " $STEPS " == *" mut_ex "* ]] && replay mut_ex expect-shift:NX:1 0 base
echo GAPS_DONE
