#!/bin/bash
# closure-loop HOLD-ECO stage (run by closure_loop.py, cwd = the job's src snapshot):
#   hold_eco.sh <route results base (5_2_route.odb)> <sign-off ORFS base (6_final.sdc)> <out dir> <block> [post-SDC (src-rel)...]
# env HM (post-route FF hold GOAL ps, default 18 = acceptance 15 + 3 for die context; the repair aims HM + ALLOW, see
#     below; a pass that routes to SS >= ACC_SS and FF >= HM ends the ECO), ALLOW (3), SM (setup margin ps kept by repair_timing, 40), FILT (endpoint filter: repair only
#     endpoints with SS setup > deficit + FILT, 40), PASSES (ECO -> re-route -> sign-off iterations, 2), RESAWARE
#     (1: resistance-aware GRT like the ORFS route), HOLDCELLS (1: HB*xp67 delay cells allowed), KEEPCLK (full re-route only, 0),
#     ACC_SS / ACC_FF (acceptance line, 15 / 15), ECO_SESSION (ff by default; auto for legacy two-corner detection),
#     WINDOW_ONLY (1: endpoint window report only, no ECO), MACROS (src-rel macro view dirs), THREADS (8), BUF (max buffer %, 30)
# per pass k (<out>/pass<k>/):
#   1. both corners' EFFECTIVE sign-off SDC from the current db (hold_eco_corner.tcl, one single-corner session each,
#      exactly corner_sta.py's read order), merged for a two-corner session (hold_eco_sdc.py)
#   2. hold_eco.tcl: FF-only session with the SS session's per-endpoint slacks and critical nets;
#      endpoint filter; repair; resistance-aware re-route (legacy auto selection is opt-in)
#   3. sign-off: tools/w18/corner_sta.py with the same post-SDCs
#   stop at the first pass that meets ACC_SS and FF >= HM; every pass starts from the original route, the next with a
#   larger hold allowance; the best pass is kept.
# -> <out>/eco.log (all passes), <out>/orfs -> the chosen pass, <out>/corner_sta.json, <out>/result.json
#    {ss_ps, ff_ps, drc, cells_added, pass, session, window}
set -eo pipefail
ECO_SESSION=${ECO_SESSION:-ff}
case "$ECO_SESSION" in ff|auto) ;; *) echo "ECO_SESSION must be ff or auto"; exit 2 ;; esac
RB=$1; OB=$2; OUT=$3; BLK=$4; shift 4
D=$(basename $(dirname $RB))
CLD=$(cd $(dirname $0) && pwd)
IMG=${ORFS_IMAGE:-openroad/orfs:asap7lock}
[ ! -e "$OUT" ] || { echo "ECO output already exists; preserving evidence: $OUT"; exit 10; }
if [ -n "${ECO_GUARD:-}" ]; then python3 "$CLD/eco_recovery.py" verify "$ECO_GUARD"; fi
mkdir -p "$OUT"
DB=5_2_route.odb; [ -f $RB/$DB ] || DB=6_final.odb   # pre-fill route db; the tcl removes fillers otherwise
CUR_DIR=$RB; CUR_DB=$DB; CUR_SPEF=$OB/6_final.spef; [ -f $CUR_SPEF ] || CUR_SPEF=$RB/6_final.spef
PS=""; for p in "$@"; do PS="$PS /src/$p"; done
MS=""; for m in ${MACROS:-}; do MS="$MS /src/$m"; done
CS_ARGS=$(for p in "$@"; do echo -n " --post-sdc $p"; done; for m in ${MACROS:-}; do echo -n " --macro $m"; done)
ACC_SS=${ACC_SS:-15}; ACC_FF=${ACC_FF:-15}
orun() {  # orun <log> <tcl> [docker -e args...]: openroad in the fleet image
  local log=$1 tcl=$2; shift 2
  docker run --rm -v $CUR_DIR:/in:ro -v $(dirname $CUR_SPEF):/inspef:ro -v $OB:/ob:ro -v $P:/p -v $PWD:/src:ro -v $CLD:/cl:ro \
    -e OT_MACROS="${MS# }" -e OT_CL=/cl "$@" $IMG bash -lc \
    "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /cl/$tcl" > $log 2>&1
}
best=""; bestscore=-1e9
for k in $(seq 1 ${PASSES:-2}); do
  P=$OUT/pass$k; EB=$P/orfs/results/asap7/$D/base; mkdir -p $EB
  cp $OB/6_final.sdc $EB/6_final.sdc
  echo "OT_PASS $k input $CUR_DIR/$CUR_DB spef $CUR_SPEF" | tee -a $OUT/eco.log
  FAILED=0
  for c in ss ff; do
    orun $P/corner_$c.log hold_eco_corner.tcl -e OT_CORNER=$c -e OT_DB=/in/$CUR_DB -e OT_SDC=/ob/6_final.sdc \
      -e OT_SPEF=/inspef/$(basename $CUR_SPEF) -e OT_POST_SDC="${PS# }" -e OT_EFF=/p/eff_$c.sdc \
      -e OT_CRIT_PS=$(awk "BEGIN{print ${SM:-40} + 20}")
    grep -q "OT_CORNER_EFF done" $P/corner_$c.log || { echo "corner $c session failed"; tail -20 $P/corner_$c.log; FAILED=1; break; }
  done
  [ $FAILED = 0 ] || { [ -n "$best" ] && break; exit 9; }   # a later pass failing keeps the best earlier pass
  python3 $CLD/hold_eco_sdc.py $P/eff_ss.sdc $P/eff_ff.sdc $P/merged.sdc >> $OUT/eco.log
  EXP_SS=$(awk '/OT_CORNER_EFF ss ws_max/{printf "%.2f", $4*1e12}' $P/corner_ss.log)
  EXP_FF=$(awk '/OT_CORNER_EFF ff ws_max/{printf "%.2f", $6*1e12}' $P/corner_ff.log)
  # repair target = HM + a post-route allowance: the repair sees the new buffers' nets without wires, so the routed hold
  # lands short (ctrl_pc / svcio_od / colt_lane: target 15 -> routed 6.5-14.6).  Pass 1 adds ALLOW (3 ps); each later
  # pass adds 1.5 x the shortfall the previous pass left under HM (allowance capped at 20 ps).
  CUR_ALLOW=$(python3 -c "a=float('${CUR_ALLOW:-${ALLOW:-3}}'); prev='${PREV_FF:-}'; hm=float('${HM:-18}')
print(a if not prev else min(20.0, a + max(0.0, 1.5 * (hm - float(prev)))))")
  TGT=$(python3 -c "print(float('${HM:-18}') + float('$CUR_ALLOW'))")
  echo "OT_PASS $k hold repair target $TGT (post-route goal ${HM:-18}, acceptance $ACC_FF)" | tee -a $OUT/eco.log
  ECO_ENV=(-e OT_DB=/in/$CUR_DB -e OT_OUT=/p/orfs/results/asap7/$D/base -e OT_HOLD_MARGIN=$TGT -e OT_SETUP_MARGIN=${SM:-40}
           -e OT_SETUP_FILTER=${FILT:-40} -e OT_ACCEPT_SS=$ACC_SS -e OT_ACCEPT_FF=$ACC_FF -e OT_HOLD_CELLS=${HOLDCELLS:-1}
           -e OT_RES_AWARE=${RESAWARE:-1} -e OT_KEEP_CLOCK=${KEEPCLK:-0} -e OT_THREADS=${THREADS:-8}
           -e OT_MAXL=${MAXL:-M7} -e OT_MAX_BUF_PCT=${BUF:-30} -e OT_WINDOW_ONLY=${WINDOW_ONLY:-0})
  # Default FF-only: matching the worst SS/FF margins does not prove that
  # every SS hold endpoint is irrelevant to a two-corner repair. Keep the
  # legacy automatic selection available only by explicit request.
  SESSION=ff
  if [ "$ECO_SESSION" = auto ]; then
    SESSION=two
    orun $P/eco_two.log hold_eco.tcl "${ECO_ENV[@]}" -e OT_SESSION=two -e OT_SDC=/p/merged.sdc -e OT_EXPECT_SS=$EXP_SS -e OT_EXPECT_FF=$EXP_FF || true
    if grep -q "OT_ECO session_mismatch" $P/eco_two.log; then
      SESSION=ff; grep "OT_ECO session_mismatch" $P/eco_two.log | tee -a $OUT/eco.log
    fi
  fi
  if [ "$SESSION" = ff ]; then
    rm -f $EB/pre_eco.spef
    orun $P/eco_ff.log hold_eco.tcl "${ECO_ENV[@]}" -e OT_SESSION=ff -e OT_SDC=/p/eff_ff.sdc \
      -e OT_SS_SLACK=/p/eff_ss.sdc.slack -e OT_SS_CRIT=/p/eff_ss.sdc.crit || true
  fi
  L=$P/eco_$SESSION.log; cat $L >> $OUT/eco.log
  if [ "${WINDOW_ONLY:-0}" = 1 ]; then grep "OT_WIN\|session" $L; exit 0; fi
  grep -q "OT_ECO done" $L || { echo "ECO pass $k failed (no OT_ECO done)"; tail -20 $L; [ -n "$best" ] && break; exit 9; }
  python3 tools/w18/corner_sta.py $CS_ARGS --orfs-dir $P/orfs --output $P/corner_sta.json > $P/corner.log 2>&1 \
    || { echo "corner_sta failed"; tail $P/corner.log; exit 8; }
  python3 - $P $k $SESSION $ACC_SS $ACC_FF <<'PY'
import json, re, sys
p, k, session, acc_ss, acc_ff = sys.argv[1], int(sys.argv[2]), sys.argv[3], float(sys.argv[4]), float(sys.argv[5])
log = open(f'{p}/eco_{session}.log').read()
nv = re.findall(r'Number of violations = (\d+)', log)
cs = json.load(open(f'{p}/corner_sta.json'))
add = re.findall(r'OT_ECO cells_added (-?\d+)', log)
win = re.findall(r'^OT_WIN pre (.*)$', log, re.M)
r = dict(ss_ps=cs['setup_ss']['worst_slack_ps'], ff_ps=cs['hold_ff']['worst_slack_ps'], drc=int(nv[-1]) if nv else None,
         cells_added=int(add[0]) if add else None, errors=cs['setup_ss'].get('errors', []) + cs['hold_ff'].get('errors', []),
         **{'pass': k}, session=session, window=win[0] if win else None)
ok = r['ss_ps'] is not None and r['ff_ps'] is not None
r['score'] = min(r['ss_ps'] - acc_ss, r['ff_ps'] - acc_ff) if ok and r['drc'] == 0 and not r['errors'] else -1e9
json.dump(r, open(f'{p}/result.json', 'w'), indent=1); print('OT_PASS_RESULT', json.dumps(r))
PY
  cat $P/result.json >> $OUT/eco.log
  sc=$(python3 -c "import json;print(json.load(open('$P/result.json'))['score'])")
  if python3 -c "import sys; sys.exit(0 if $sc > $bestscore else 1)"; then best=$P; bestscore=$sc; fi
  # done when the routed result meets the post-route goal (FF >= HM), not merely the acceptance line
  python3 -c "import json,sys; r=json.load(open('$P/result.json')); sys.exit(0 if r['score'] >= 0 and r['ff_ps'] >= float('${HM:-18}') else 1)" && break
  # the next pass restarts from the ORIGINAL route (its GRT guides intact) with a larger allowance: chaining passes on an
  # ECO'd db hit DRT-0218 'Guide is not connected to design' (capt_x, hfd_svc_SE_s6 pass 2)
  PREV_FF=$(python3 -c "import json;print(json.load(open('$P/result.json'))['ff_ps'])")
done
[ -n "$best" ] || { echo "no ECO pass produced a result"; exit 9; }
ln -sfn $(basename $best)/orfs $OUT/orfs
cp $best/corner_sta.json $OUT/corner_sta.json
cp $best/result.json $OUT/result.json
echo "OT_ECO chosen $(basename $best)" | tee -a $OUT/eco.log
grep "Number of violations" $best/eco_*.log | tail -1 >> $OUT/eco.log || true
cat $OUT/result.json
