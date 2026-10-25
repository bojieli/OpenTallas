#!/bin/bash
# TOK-DS deskew-cut NX replay (Claude, 10-25): compile L0 against the deskew XRT source root (ec43, exactly the RTL in the
# dsk_cuts binaries), extract the entry/norm NX arithmetic phase (norm_phase.py, nx_delta 0), compare it with Codex's
# codex_nx138 vehicle, then per cut: gen base / mut_in (input corrupt) / mut_ex (expect-shift:NX:1), sim, check.
# Usage: replay_dsk.sh <out dir> <steps: compile|cuts> [cut ...]
set -u
O=$1; STEP=$2; shift 2
T=/srv/opentallas-scratch2/claude/wt/codex-tok-ds-1025
S=/srv/opentallas-scratch2/claude/tok-ds; W=$S/fc31; C=$S/dsk_cuts
export OT_S81_SELECTED_DEFINES=DSFD_PQ_STATIC_X2,S81CTRL_SRAM_FIFO,S81CTRL_SRAM_P192,S81CTRL_NATIVE32,OT_COLL_NATIVE32,OT_COLL_NATIVE32_OFF,OT_S81ENG_TAP_N32R2,OT_S81SL_KV_TRANSPORT,OT_SVC_ALLQ,SU_SMU_T,SVCQ_ENG_FG3
export OT_S81_SELECTED_SOURCE_ROOT=$S/stw-s81d-tok/layers/root31dsk OT_SVC_ALLQ=1
export OT_XS_FRAME_SCHEDULE_DIR=$W/layers_fc31/frame_schedules
PROOF=${PROOF:-$S/runs/claude_dsk/entry_ec43/entry_replay.json}
DIE=$W/tree_fc31/results/arch/s81_dv_1016/bind9/die.v.gz; PF=$O/prog_full; P=$O/prog_L0_su
mkdir -p $O; cd $T
if [ $STEP = compile ]; then
  [ -e $PF ] && { echo "exists $PF"; exit 3; }
  /usr/bin/time -v -o $O/cc.time python3 tools/s81_dv/dv_layer_compile.py --layer L0 --out $PF --die-src $W/tree_fc31 \
    --fixtures $S/stw-s81d-tok/layers/fix/L0 --entry-norm-check all > $O/cc.log 2> $O/cc.err || { echo "compile FAIL"; tail -5 $O/cc.err; exit 1; }
  python3 tools/s81_dv/layer_prog/norm_phase.py $PF $P > $O/phase.log 2>&1 || { echo "phase FAIL"; cat $O/phase.log; exit 1; }
  python3 - $P $S/runs/codex_nx138/prog_L0_su > $O/nx_compare.json <<'PY'
import json,sys
def nx(p):
    S=json.load(open(p+'/schedule.json'))
    return S, sorted((e.get('tag'),e.get('inst'),e['cycle'],json.dumps(e.get('words'))) for e in S['events'] if e.get('kind')=='NX')
a,na=nx(sys.argv[1]); b,nb=nx(sys.argv[2])
ev=lambda S: sorted(json.dumps({k:v for k,v in e.items()},sort_keys=True) for e in S['events'])
ea,eb=ev(a),ev(b)
print(json.dumps(dict(new=sys.argv[1], codex_nx138=sys.argv[2], nx_new=len(na), nx_old=len(nb), nx_identical=na==nb,
  events_new=len(ea), events_old=len(eb), events_identical=ea==eb,
  contract_new=a.get('timing_contract',{}).get('transport_sources'), contract_old=b.get('timing_contract',{}).get('transport_sources')),indent=1))
PY
  cat $O/nx_compare.json; exit 0
fi
T0=$(python3 -c "import json; S=json.load(open('$P/schedule.json')); print(max(100, 100 - min(e['cycle'] for e in S['events'])))")
replay() {  # cut name mutant sim(0/1) [trace-of]
  local CUT=$1 R=$O/L0/$1/$2
  [ ! -e "$R" ] || { echo "$CUT $2: $R exists"; return 3; }
  mkdir -p $R
  python3 tools/s81_dv/dv_cut_replay.py gen --die-v $DIE --prog $P --cut $C/$CUT --out $R --t0 $T0 ${3:+--mutant $3} > $R/gen.log 2>&1 \
    || { echo "$CUT $2 gen FAIL: $(tail -1 $R/gen.log)"; return 1; }
  local RUN=$R/run
  if [ "$4" = 1 ]; then
    NC=$(python3 -c "import json; print(json.load(open('$R/replay.json'))['ncyc'])")
    OBJ=$C/out_$CUT/obj J=1 bash tools/s81_dv/run_dv_slice.sh $C/K_$CUT $RUN +IN=$R/in.txt +OUT=$R/out.txt \
      +TRACE=$RUN/trace.txt +NCYC=$NC > $R/sim.log 2>&1
  else RUN=$O/L0/$CUT/$5/run; fi
  if [ -e $PROOF ]; then export OT_S81_XRT_RUNTIME_PROOF=$PROOF; fi
  python3 tools/s81_dv/dv_cut_replay.py check --replay $R --run $RUN --out $R/check.json > $R/check.log 2>&1
  echo "$CUT $2 t0 $T0: $(grep -h '^DV_SLICE ' $RUN/run.log) | $(tail -1 $R/check.log)"
}
for CUT in "$@"; do
  case $CUT in cut_0S) MI=corrupt:xrW_0S_l0:91;; cut_0N) MI=corrupt:xrW_0N_l0:91;; cut_7) MI=corrupt:xrE_6S_l0:91:14;; esac
  [ -x $C/out_$CUT/obj/sim ] || { echo "$CUT NOT RUN: no binary"; continue; }
  replay $CUT base "" 1; replay $CUT mut_in $MI 1; replay $CUT mut_ex expect-shift:NX:1 0 base
done
echo REPLAY_DONE
