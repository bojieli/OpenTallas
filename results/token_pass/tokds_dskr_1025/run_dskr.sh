#!/bin/bash
# TOK-DS dskr (10-25): deskew L0 NX replay chain on the vehicles from prep_dskr.sh / mk_srcroot_dskr.py, every tool from this
# checkout (repo-relative), selected sources = <W>/src. Successor of results/token_pass/tokds_dsk_replay_1025 (ec43, lost).
#   run_dskr.sh <W> fs|compile|receipt|entry|cuts [cut ...]
# <W> holds veh/ (prep_dskr.sh), src/ (mk_srcroot_dskr.py), fix/L0 (fixtures; sha-checked vs results/rtl/s81_layer_tput_1018),
# builds/out_<cut>/obj/sim (tools/s81_dv/run_dv_slice.sh on veh/cuts/K_<cut>), runs/ (outputs).
set -u
W=$(realpath $1); STEP=$2; shift 2
R=$(cd "$(dirname "$0")" && git rev-parse --show-toplevel); cd $R
export OT_S81_SELECTED_DEFINES=DSFD_PQ_STATIC_X2,S81CTRL_SRAM_FIFO,S81CTRL_SRAM_P192,S81CTRL_NATIVE32,OT_COLL_NATIVE32,OT_COLL_NATIVE32_OFF,OT_S81ENG_TAP_N32R2,OT_S81SL_KV_TRANSPORT,OT_SVC_ALLQ,SU_SMU_T,SVCQ_ENG_FG3
export OT_S81_SELECTED_SOURCE_ROOT=$W/src OT_SVC_ALLQ=1 OT_XS_FRAME_SCHEDULE_DIR=$W/runs/frame_schedules
T=$W/veh/tree_fc31; F=$W/fix/L0; C=$W/veh/cuts; B=$W/builds; O=$W/runs; DIE=$T/results/arch/s81_dv_1016/bind9/die.v.gz
PF=$O/prog_full; P=$O/prog_L0_su; REC=$O/entry_mechanism_dskr.json; EJ=$O/entry_jobs; EP=$O/entry_replay
PROOF=$EP/entry_replay.json; mkdir -p $O
case $STEP in
fs)
  python3 - $R/results/rtl/s81_layer_tput_1018/fixtures/L0.sha256.json $F <<'PY' || exit 2
import hashlib, json, sys
from pathlib import Path
m = json.load(open(sys.argv[1])); F = Path(sys.argv[2])
bad = [k for k, v in m['files'].items() if hashlib.sha256((F / k).read_bytes()).hexdigest() != v]
print('FIXTURES L0', len(m['files']), 'files', 'OK' if not bad else f'BAD {bad[:5]}'); sys.exit(1 if bad else 0)
PY
  [ -e $O/frame_schedules ] && { echo "exists"; exit 3; }
  python3 tools/s81_dv/tokfunc/prepare_frame_schedules.py --tree $T --out $O/frame_schedules > $O/frame_schedules.log 2>&1
  echo "FS rc $? $(tail -1 $O/frame_schedules.log | cut -c1-200)";;
compile)
  [ -e $PF ] && { echo "exists $PF"; exit 3; }
  /usr/bin/time -v -o $O/cc.time python3 tools/s81_dv/dv_layer_compile.py --layer L0 --out $PF --die-src $T --fixtures $F \
    --entry-norm-check all > $O/cc.log 2> $O/cc.err || { echo "compile FAIL"; tail -5 $O/cc.err; exit 1; }
  python3 tools/s81_dv/layer_prog/norm_phase.py $PF $P > $O/phase.log 2>&1 || { echo "phase FAIL"; cat $O/phase.log; exit 1; }
  echo "COMPILE OK $(tail -1 $O/phase.log | cut -c1-200)";;
receipt)
  python3 tools/s81_dv/layer_prog/entry_mechanism.py --w-result $O/entry_vp/w1/result.json --ev-result $O/entry_vp/ev1/result.json \
    --out $REC; echo "RECEIPT rc $?";;
entry)
  [ -e $EJ ] || python3 tools/s81_dv/layer_prog/entry_boot.py --tree $T --fixtures $F --mechanism-receipt $REC --out $EJ \
    --replay-job 15 --replay-job 16 --replay-job 17 --replay-job 20 --replay-job 21 --replay-job 22 > $O/entry_boot.log 2>&1 \
    || { echo "entry_boot FAIL"; tail -5 $O/entry_boot.log; exit 1; }
  [ -e $EP ] && { echo "exists $EP"; exit 3; }
  python3 tools/s81_dv/tokfunc/run_entry_replay.py --src $W/src --die-v $DIE --cut $C/cut_3S_ctl --kit $C/K_cut_3S_ctl \
    --obj $B/out_cut_3S_ctl/obj --idle-run $B/out_cut_3S_ctl --progs $EJ --fixture-meta $F/meta.json --ks-user 0 --out $EP \
    --jobs 15 16 17 20 21 22 --mutant 15:corrupt:hf_7N_l0:33 --ks-probe --par 8 > $O/entry_replay.log 2>&1
  echo "ENTRY rc $? $(grep ENTRY_REPLAY $O/entry_replay.log | tail -1)";;
cuts)
  T0=$(python3 -c "import json; S=json.load(open('$P/schedule.json')); print(max(100, 100 - min(e['cycle'] for e in S['events'])))")
  [ -e $PROOF ] && export OT_S81_XRT_RUNTIME_PROOF=$PROOF
  replay() {  # cut mutant-name mutant sim(0/1) [trace-of]
    local CUT=$1 R2=$O/L0/$1/$2; [ ! -e "$R2" ] || { echo "$CUT $2: exists"; return 3; }; mkdir -p $R2
    python3 tools/s81_dv/dv_cut_replay.py gen --die-v $DIE --prog $P --cut $C/$CUT --out $R2 --t0 $T0 ${3:+--mutant $3} \
      > $R2/gen.log 2>&1 || { echo "$CUT $2 gen FAIL: $(tail -1 $R2/gen.log)"; return 1; }
    local RUN=$R2/run
    if [ "$4" = 1 ]; then
      NC=$(python3 -c "import json; print(json.load(open('$R2/replay.json'))['ncyc'])")
      OBJ=$B/out_$CUT/obj J=1 bash tools/s81_dv/run_dv_slice.sh $C/K_$CUT $RUN +IN=$R2/in.txt +OUT=$R2/out.txt \
        +TRACE=$RUN/trace.txt +NCYC=$NC > $R2/sim.log 2>&1
    else RUN=$O/L0/$CUT/$5/run; fi
    python3 tools/s81_dv/dv_cut_replay.py check --replay $R2 --run $RUN --out $R2/check.json > $R2/check.log 2>&1
    echo "$CUT $2 t0 $T0: $(grep -h '^DV_SLICE ' $RUN/run.log) | $(tail -1 $R2/check.log | cut -c1-300)"
  }
  for CUT in "$@"; do
    case $CUT in cut_0S) MI=corrupt:xrW_0S_l0:91;; cut_0N) MI=corrupt:xrW_0N_l0:91;; cut_7) MI=corrupt:xrE_6S_l0:91:14;; esac
    [ -x $B/out_$CUT/obj/sim ] || { echo "$CUT NOT RUN: no binary"; continue; }
    replay $CUT base "" 1; replay $CUT mut_in $MI 1; replay $CUT mut_ex expect-shift:NX:1 0 base
  done; echo REPLAY_DONE;;
*) echo "unknown step $STEP"; exit 2;;
esac
