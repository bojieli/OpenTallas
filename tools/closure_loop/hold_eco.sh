#!/bin/bash
# closure-loop HOLD-ECO stage (run by closure_loop.py, cwd = the job's src snapshot):
#   hold_eco.sh <route results base (5_2_route.odb)> <sign-off ORFS base (6_final.sdc)> <out dir> <block> [post-SDC (src-rel)...]
# env HM (post-route FF hold GOAL ps, default 18 = acceptance 15 + 3 for die context; the repair aims HM + ALLOW, see
#     below; a pass that routes to SS >= ACC_SS and FF >= HM ends the ECO), ALLOW (12: the re-route costs 12-16 ps of the repaired FF hold, ctl r6 / router dv12 / stn_r38 pass 1), SM (setup margin ps kept by repair_timing, 40), FILT (endpoint filter: repair only
#     endpoints with SS setup > deficit + FILT, 40), PASSES (ECO -> re-route -> sign-off iterations, 2), RESAWARE
#     (1: resistance-aware GRT like the ORFS route), HOLDCELLS (1: HB*xp67 delay cells allowed), KEEPCLK (full re-route only, 0),
#     SETUP_LIB (SS | TT: library corner of the setup scene "ss"; OWNER OPTION B 2026-10-07 -> TT),
#     SDC_NAME (the route's SIGN-OFF SDC basename in the sign-off base, e.g. 6_signoff.sdc; default 6_final.sdc): every
#     corner session, the ECO base's 6_final.sdc and the sign-off corner_sta use it, never the planning/route SDC,
#     SETUP_POST_SDC (src-rel SDCs re-timing the SETUP corners only, e.g. physical/common_flow/nbr_clk_measured.sdc: the
#     route's measured neighbour clock; corner_sta.json setup_post_sdc); setup is judged at TT (setup_tt, tt_ps),
#     ACC_SS / ACC_FF (acceptance line, 15 / 15), ECO_SESSION (mm by default = rev 3 multi-mode; ff = FF-only; auto = legacy two-corner detection),
#     ALLOW_FRESH_GRT (0 by default; 1 permits fresh routing with explicit result provenance, unchanged acceptance),
#     FREEZE / KEEPWIRES (0: opt-in macro-output / untouched-net wire preservation; rejected wires retry in a fresh process),
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
#    {ss_ps (= tt_ps: setup at TT, option B), tt_ps, ss_sensitivity_ps, ff_ps, drc, sdc_name, setup_post_sdc, cells_added, pass, session, window}
set -eo pipefail
ECO_SESSION=${ECO_SESSION:-mm}
case "$ECO_SESSION" in mm|ff|auto) ;; *) echo "ECO_SESSION must be mm, ff or auto"; exit 2 ;; esac
RB=$1; OB=$2; OUT=$3; BLK=$4; shift 4
D=$(basename $(dirname $RB))
CLD=$(cd $(dirname $0) && pwd)
IMG=${ORFS_IMAGE:-openroad/orfs:asap7lock}
[ ! -e "$OUT" ] || { echo "ECO output already exists; preserving evidence: $OUT"; exit 10; }
if [ -n "${ECO_GUARD:-}" ]; then python3 "$CLD/eco_recovery.py" verify "$ECO_GUARD"; fi
mkdir -p "$OUT"
# mtp-lead 2026-10-09: per-job opt-in knobs in <run>/hold_eco_opts.env (CLD = <run>/cl), e.g. REPAIR_DRV=1 DRV_SLEW_MARGIN=50.
# Only REPAIR_DRV / DRV_SLEW_MARGIN / DRV_CAP_MARGIN / DRV_MAX_WIRE are read from it; absent file = default ECO, unchanged.
if [ -f "$CLD/../hold_eco_opts.env" ]; then
  while IFS='=' read -r k v; do case "$k" in REPAIR_DRV|DRV_SLEW_MARGIN|DRV_CAP_MARGIN|DRV_MAX_WIRE) [[ "$v" =~ ^[0-9.]+$ ]] && export "$k=$v" ;; esac; done < "$CLD/../hold_eco_opts.env"
  echo "OT_ECO job opts: REPAIR_DRV=${REPAIR_DRV:-0} DRV_SLEW_MARGIN=${DRV_SLEW_MARGIN:-30} DRV_CAP_MARGIN=${DRV_CAP_MARGIN:-20} DRV_MAX_WIRE=${DRV_MAX_WIRE:-0}" | tee "$OUT/job_opts.log"
fi
DB=${ECO_RB_DB:-5_2_route.odb}; [ -f $RB/$DB ] || DB=6_final.odb   # ECO_RB_DB=6_final.odb: stacked ECO on an installed ECO (drive-1243)
# (pre-fill route db; the tcl removes fillers otherwise)
CUR_DIR=$RB; CUR_DB=$DB; CUR_SPEF=$OB/6_final.spef; [ -f $CUR_SPEF ] || CUR_SPEF=$RB/6_final.spef
PS=""; for p in "$@"; do PS="$PS /src/$p"; done
MS=""; for m in ${MACROS:-}; do MS="$MS /src/$m"; done
CS_ARGS=$(for p in "$@"; do echo -n " --post-sdc $p"; done; for m in ${MACROS:-}; do echo -n " --macro $m"; done)
ACC_SS=${ACC_SS:-15}; ACC_FF=${ACC_FF:-15}
# LOOP-GAPS 2026-10-08 (redesign-0315: hbm_smh_front_s m3f/m3g ECOs close at TT +100 / FF +20 but were scored at SS with
# the planning neighbour clock): the ECO is timed and judged with the job's own sign-off SDC set.
export SDC_NAME=${SDC_NAME:-6_final.sdc}
[ -f "$OB/$SDC_NAME" ] || { echo "sign-off SDC $OB/$SDC_NAME missing"; exit 2; }
SPS=""; for p in ${SETUP_POST_SDC:-}; do SPS="$SPS /src/$p"; done
SN=""; grep -q -- "--sdc-name" tools/w18/corner_sta.py && SN="--sdc-name $SDC_NAME"
seed_sdc() {  # the ECO base carries the sign-off SDC (also as 6_final.sdc: a corner_sta.py without --sdc-name reads it)
  cp "$OB/$SDC_NAME" "$EB/6_final.sdc"; [ "$SDC_NAME" = 6_final.sdc ] || cp "$OB/$SDC_NAME" "$EB/$SDC_NAME"
}
# MULTI-VT (2026-10-07): a route with LVT/SLVT cells is timed with those libraries too (absent: RVT only, unchanged)
OT_VT="RVT"; for t in L SL; do grep -aqE "_ASAP7_75t_${t}([^A-Za-z0-9_]|\$)" $RB/$DB && OT_VT="$OT_VT $([ $t = L ] && echo LVT || echo SLVT)"; done
orun() {  # orun <log> <tcl> [docker -e args...]: openroad in the fleet image
  local log=$1 tcl=$2; shift 2
  docker run --rm -v $CUR_DIR:/in:ro -v $(dirname $CUR_SPEF):/inspef:ro -v $OB:/ob:ro -v $P:/p -v $PWD:/src:ro -v $CLD:/cl:ro \
    -e OT_MACROS="${MS# }" -e OT_VT="$OT_VT" -e OT_CL=/cl -e OT_SETUP_LIB=${SETUP_LIB:-SS} "$@" $IMG bash -lc \
    "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /cl/$tcl" > $log 2>&1
}
best=""; bestscore=-1e9
for k in $(seq 1 ${PASSES:-2}); do
  P=$OUT/pass$k; EB=$P/orfs/results/asap7/$D/base; mkdir -p $EB
  seed_sdc
  echo "OT_PASS $k input $CUR_DIR/$CUR_DB spef $CUR_SPEF" | tee -a $OUT/eco.log
  FAILED=0
  for c in ss ff; do
    CPS="$PS"; [ $c = ss ] && CPS="$PS$SPS"     # setup-only post SDCs (measured neighbour clock) on the setup scene
    orun $P/corner_$c.log hold_eco_corner.tcl -e OT_CORNER=$c -e OT_DB=/in/$CUR_DB -e OT_SDC=/ob/$SDC_NAME \
      -e OT_SPEF=/inspef/$(basename $CUR_SPEF) -e OT_POST_SDC="${CPS# }" -e OT_EFF=/p/eff_$c.sdc \
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
  CUR_ALLOW=$(python3 -c "a=float('${CUR_ALLOW:-${ALLOW:-12}}'); prev='${PREV_FF:-}'; hm=float('${HM:-18}')
print(a if not prev else min(20.0, a + max(0.0, 1.5 * (hm - float(prev)))))")
  TGT=$(python3 -c "print(float('${HM:-18}') + float('$CUR_ALLOW'))")
  echo "OT_PASS $k hold repair target $TGT (post-route goal ${HM:-18}, acceptance $ACC_FF)" | tee -a $OUT/eco.log
  ECO_ENV=(-e OT_DB=/in/$CUR_DB -e OT_OUT=/p/orfs/results/asap7/$D/base -e OT_HOLD_MARGIN=$TGT -e OT_SETUP_MARGIN=${SM:-40}
           -e OT_SETUP_FILTER=${FILT:-40} -e OT_ACCEPT_SS=$ACC_SS -e OT_ACCEPT_FF=$ACC_FF -e OT_HOLD_CELLS=${HOLDCELLS:-1}
           -e OT_RES_AWARE=${RESAWARE:-1} -e OT_KEEP_CLOCK=${KEEPCLK:-0} -e OT_THREADS=${THREADS:-8}
           -e OT_MAXL=${MAXL:-M7} -e OT_MAX_BUF_PCT=${BUF:-30} -e OT_WINDOW_ONLY=${WINDOW_ONLY:-0}
           -e OT_ALLOW_FRESH_GRT=${ALLOW_FRESH_GRT:-0} -e OT_FREEZE_MACRO_NETS=${FREEZE:-0} -e OT_KEEP_UNTOUCHED=${KEEPWIRES:-0}
           -e OT_REPAIR_DRV=${REPAIR_DRV:-0} -e OT_DRV_SLEW_MARGIN=${DRV_SLEW_MARGIN:-30} -e OT_DRV_CAP_MARGIN=${DRV_CAP_MARGIN:-20}
           -e OT_DRV_MAX_WIRE=${DRV_MAX_WIRE:-0})
  # Multi-mode must reproduce both sign-off corners or fall back to FF-only.
  # Legacy merged-corner selection remains an explicit request.
  SESSION=ff
  if [ "$ECO_SESSION" = mm ]; then
    # rev 3 default: multi-mode session (scene ss: SS effective SDC with hold false-pathed; scene ff: FF effective SDC
    # with setup false-pathed), used only if it reproduces sign-off; otherwise the FF-only session
    SESSION=mm
    { cat $P/eff_ss.sdc; echo 'set_false_path -hold -to [all_clocks]'; } > $P/mode_ss.sdc
    { cat $P/eff_ff.sdc; echo 'set_false_path -setup -to [all_clocks]'; } > $P/mode_ff.sdc
    SARGS=(-e OT_SESSION=mm -e OT_SDC_SS=/p/mode_ss.sdc -e OT_SDC_FF=/p/mode_ff.sdc \
      -e OT_PRE_SPEF=/inspef/$(basename $CUR_SPEF) \
      -e OT_EXPECT_SS=$EXP_SS -e OT_EXPECT_FF=$EXP_FF)
    orun $P/eco_mm.log hold_eco.tcl "${ECO_ENV[@]}" "${SARGS[@]}" || true
    if grep -q "OT_ECO session_mismatch" $P/eco_mm.log; then
      SESSION=ff; grep "OT_ECO session_mismatch" $P/eco_mm.log | tee -a $OUT/eco.log
    fi
  fi
  if [ "$ECO_SESSION" = auto ]; then
    SESSION=two
    SARGS=(-e OT_SESSION=two -e OT_SDC=/p/merged.sdc -e OT_EXPECT_SS=$EXP_SS -e OT_EXPECT_FF=$EXP_FF)
    orun $P/eco_two.log hold_eco.tcl "${ECO_ENV[@]}" "${SARGS[@]}" || true
    if grep -q "OT_ECO session_mismatch" $P/eco_two.log; then
      SESSION=ff; grep "OT_ECO session_mismatch" $P/eco_two.log | tee -a $OUT/eco.log
    fi
  fi
  if [ "$SESSION" = ff ]; then
    rm -f $EB/pre_eco.spef
    SARGS=(-e OT_SESSION=ff -e OT_SDC=/p/eff_ff.sdc -e OT_SS_SLACK=/p/eff_ss.sdc.slack -e OT_SS_CRIT=/p/eff_ss.sdc.crit)
    orun $P/eco_ff.log hold_eco.tcl "${ECO_ENV[@]}" "${SARGS[@]}" || true
  fi
  L=$P/eco_$SESSION.log
  if grep -q "OT_ECO freeze_rejected" $L; then
    # DRT refused the kept wires: the same pass in a FRESH session with every wire stripped (a 2nd detailed_route in one
    # session corrupted it on cmdproc_n)
    grep "OT_ECO freeze_rejected" $L | tee -a $OUT/eco.log; mv $L $P/eco_${SESSION}_kept.log
    mv "$EB" "${EB}_kept"
    mkdir -p "$EB"
    cp "$OB/${SDC_NAME:-6_final.sdc}" "$EB/6_final.sdc"   # = seed_sdc (spelled out: the retry block is unit-tested alone)
    orun $L hold_eco.tcl "${ECO_ENV[@]}" "${SARGS[@]}" -e OT_FREEZE_MACRO_NETS=0 -e OT_KEEP_UNTOUCHED=0 || true
  fi
  cat $L >> $OUT/eco.log
  if [ "${WINDOW_ONLY:-0}" = 1 ]; then grep "OT_WIN\|session" $L; exit 0; fi
  grep -q "OT_ECO done" $L || { echo "ECO pass $k failed (no OT_ECO done)"; tail -20 $L; [ -n "$best" ] && break; exit 9; }
  seed_sdc   # the ECO may have rewritten the base's SDC
  python3 tools/w18/corner_sta.py $CS_ARGS $SN --orfs-dir $P/orfs --output $P/corner_sta.json > $P/corner.log 2>&1 \
    || { echo "corner_sta failed"; tail $P/corner.log; exit 8; }
  if [ -n "${SETUP_POST_SDC:-}" ]; then   # setup corners re-timed with the measured neighbour clock (the route's own merge)
    python3 tools/w18/corner_sta.py $CS_ARGS $(for q in $SETUP_POST_SDC; do echo -n " --post-sdc $q"; done) $SN \
      --orfs-dir $P/orfs --output $P/corner_sta_setup_post.json > $P/corner_setup_post.log 2>&1 \
      || { echo "setup post-SDC corner_sta failed"; tail $P/corner_setup_post.log; exit 8; }
    cp $P/corner_sta.json $P/corner_sta_hold_model.json
    python3 -c "import json,sys; b=json.load(open(sys.argv[1])); p=json.load(open(sys.argv[2]))
for k in ('setup_tt', 'setup_ss'):
    if k in p: b[k] = p[k]
b['setup_post_sdc'] = p['post_sdc']; json.dump(b, open(sys.argv[1], 'w'), indent=1)" $P/corner_sta.json $P/corner_sta_setup_post.json
  fi
  if ! python3 -c "import json,sys; sys.exit(0 if 'setup_tt' in json.load(open('$P/corner_sta.json')) else 1)"; then
    # a snapshot corner_sta.py that predates option B: TT re-STA of its own (last-written) setup script
    bash $CLD/tt_resta.sh $P/orfs $PWD $P/corner_sta.tt.json > $P/tt_resta.log 2>&1 || true
    python3 -c "import json,sys; b=json.load(open(sys.argv[1])); t=json.load(open(sys.argv[2]))
b['setup_tt'] = t.get('setup_tt') or dict(corner='tt', worst_slack_ps=None, errors=[t.get('error', 'tt_resta failed')])
json.dump(b, open(sys.argv[1], 'w'), indent=1)" $P/corner_sta.json $P/corner_sta.tt.json \
      || { echo "TT re-STA failed"; tail $P/tt_resta.log; exit 8; }
  fi
  python3 - $P $k $SESSION $ACC_SS $ACC_FF <<'PY'
import json, os, re, sys
p, k, session, acc_ss, acc_ff = sys.argv[1], int(sys.argv[2]), sys.argv[3], float(sys.argv[4]), float(sys.argv[5])
log = open(f'{p}/eco_{session}.log').read()
nv = re.findall(r'Number of violations = (\d+)', log)
cs = json.load(open(f'{p}/corner_sta.json'))
add = re.findall(r'OT_ECO cells_added (-?\d+)', log)
win = re.findall(r'^OT_WIN pre (.*)$', log, re.M)
route_strategy = re.findall(r'^OT_ECO route_strategy (.*)$', log, re.M)
su = cs['setup_tt']   # OWNER OPTION B: setup closes at TT (setup_tt always present: corner_sta.py or tt_resta.sh above)
r = dict(ss_ps=su['worst_slack_ps'], tt_ps=su['worst_slack_ps'], ff_ps=cs['hold_ff']['worst_slack_ps'],
         drc=int(nv[-1]) if nv else None, sdc_name=os.environ.get("SDC_NAME", "6_final.sdc"),
         setup_post_sdc=list(cs.get('setup_post_sdc') or []),
         setup_corner=su.get('corner', 'tt'), ss_sensitivity_ps=cs['setup_ss']['worst_slack_ps'],
         cells_added=int(add[0]) if add else None, errors=su.get('errors', []) + cs['hold_ff'].get('errors', []),
         **{'pass': k}, session=session, window=win[0] if win else None, route_strategy=route_strategy)
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
