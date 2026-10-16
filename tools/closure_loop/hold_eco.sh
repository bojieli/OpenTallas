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
# Explicit A native-capture recovery only. The plan is source-pinned, hash-bound,
# and reapplied in each fresh session from the same immutable original ODB.
# Normal hold repair, routing, extraction and TT/FF acceptance remain unchanged.
NATIVE_NORMALIZE_ENV=()
if [ -n "${NATIVE_NORMALIZE_TCL:-}" ]; then
  [[ "${NATIVE_NORMALIZE_SHA256:-}" =~ ^[0-9a-f]{64}$ ]] || { echo "native normalization needs SHA256"; exit 2; }
  NATIVE_REAL=$(realpath "$NATIVE_NORMALIZE_TCL")
  case "$NATIVE_REAL" in "$PWD"/*) ;; *) echo "native normalization must be inside source snapshot"; exit 2 ;; esac
  [ -f "$NATIVE_REAL" ] || { echo "native normalization source missing"; exit 2; }
  [ "$(sha256sum "$NATIVE_REAL" | cut -d ' ' -f 1)" = "$NATIVE_NORMALIZE_SHA256" ] || { echo "native normalization hash mismatch"; exit 2; }
  NATIVE_REL=${NATIVE_REAL#"$PWD"/}
  NATIVE_NORMALIZE_ENV=(-e OT_ECO_NATIVE_NORMALIZE=/src/$NATIVE_REL -e OT_ECO_NATIVE_NORMALIZE_SHA256=$NATIVE_NORMALIZE_SHA256)
fi
ECO_SESSION=${ECO_SESSION:-mm}
case "$ECO_SESSION" in mm|ff|auto) ;; *) echo "ECO_SESSION must be mm, ff or auto"; exit 2 ;; esac
RB=$1; OB=$2; OUT=$3; BLK=$4; shift 4
D=$(basename $(dirname $RB))
CLD=$(cd $(dirname $0) && pwd)
IMG=${ORFS_IMAGE:-openroad/orfs:asap7lock}
# DEAD-ECO (drive-1010 2026-10-10): an ECO killed by a host hang left $OUT without result.json and every re-run
# refused (exit 10). A finished ECO (result.json present) is still never overwritten; an unfinished one is moved aside.
if [ -e "$OUT" ]; then
  if [ -e "$OUT/result.json" ]; then echo "ECO output already exists; preserving evidence: $OUT"; exit 10; fi
  mv "$OUT" "$OUT.dead-$(date +%Y%m%dT%H%M%S)" && echo "ECO output without result.json (dead run) moved aside: $OUT"
fi
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
MACROS=${MACROS:-}
if [ -n "$MACROS" ]; then  # MACRO-VIEW (2026-10-11): a bare SRAM master in verdict.macros crashed every ECO (ORD-0001)
  MACROS=$(python3 "$CLD/macro_views.py" --root "$PWD" $MACROS) || { echo "MACROS unresolvable against the source snapshot: refusing to run without the macro LEF/lib"; exit 2; }
fi
MS=""; for m in ${MACROS:-}; do MS="$MS /src/$m"; done
CS_ARGS=$(for p in "$@"; do echo -n " --post-sdc $p"; done; for m in ${MACROS:-}; do echo -n " --macro $m"; done)
ACC_SS=${ACC_SS:-15}; ACC_FF=${ACC_FF:-15}
# el1011-q-tile 2026-10-11: the ECO re-route keeps the block's own routing-layer contract.  The hard default M7 re-routed
# a hardened leaf (MAX_ROUTING_LAYER M6: M7 left free for its parent's straps) with ~1.8k signal shapes on M7 (qfd_tile_lsl4);
# MAXL defaults to the route's config.mk MAX_ROUTING_LAYER, M7 only when the route sets none.
if [ -z "${MAXL:-}" ]; then
  CFGMK=${ROUTE_CFG:-$(dirname $(dirname $(dirname $(dirname $RB))))/config.mk}
  [ -f "$CFGMK" ] && MAXL=$(sed -n 's/^export MAX_ROUTING_LAYER *= *//p' "$CFGMK" | tail -1 | tr -d ' ')
  echo "OT_ECO max routing layer ${MAXL:-M7} (route config: $CFGMK)" | tee -a "$OUT/eco.log"
fi
# LOOP-GAPS 2026-10-08 (redesign-0315: hbm_smh_front_s m3f/m3g ECOs close at TT +100 / FF +20 but were scored at SS with
# the planning neighbour clock): the ECO is timed and judged with the job's own sign-off SDC set.
# FACE-PIN KEEPOUT IN THE ECO RE-ROUTE (el1011-ds-misc 2026-10-12).  The ECO strips and re-routes every signal net, but
# the route's PRE_GLOBAL_ROUTE face-pin keepout (stn_pin_keepout.tcl via OT_RM_PK / *_pk.tcl / rm_chain / pinko) was
# removed at POST_DETAIL_ROUTE, so the ECO DRT ran neighbouring nets on the layer above the face pins again: the 4
# closed tiles with child_lint (f) blocked pins in blocked_pin_sweep.json (deb7208eb: engc pbc 187/684, ws 58/1717,
# win 15/801, pqc qb 44/1105) are exactly the 4 that went through a hold ECO; the 9 without ECO have 0.  When the
# route's config.mk hooks carried a keepout, the ECO session re-applies it ABOVE ONLY (OT_PK_FRAC / HALO / FACES from
# the route) around its GRT/DRT and removes it before export.  ECO_PK=0 opts out, ECO_PK=1 forces it.
# ROUTE-CFG (2026-10-12, dscoll_cesn_rt-rta): a combo ECO stacks this script on vtswap_eco.sh's output base, whose ORFS
# dir has no config.mk, so MAXL fell back to M7 and the keepout to 0: the ECO re-route of an M2-M6 tile put 5,573 shapes
# on M7 and blocked 276 face pins (child_lint (c)+(f) FAIL at export after CLOSED).  The loop passes the ORIGINAL route's
# config.mk as ROUTE_CFG; without it a missing config.mk is reported loudly.
RCFG=${ROUTE_CFG:-$(dirname $(dirname $(dirname $(dirname $RB))))/config.mk}
[ -f "$RCFG" ] || echo "OT_ECO WARNING: route config $RCFG missing -> layer cap / face-pin keepout of the route NOT applied" | tee -a "$OUT/eco.log"
if [ -z "${ECO_PK:-}" ]; then
  ECO_PK=0
  if [ -f "$RCFG" ]; then
    for hk in $(sed -n 's/^export \(PRE_GLOBAL_ROUTE_TCL\|POST_DETAIL_ROUTE_TCL\) *= *//p' "$RCFG"); do
      case "$hk" in *_pk.tcl|*pinko*|*stn_pin_keepout*) ECO_PK=1;; esac
      for hf in $(find "$(dirname "$RCFG")/.." -maxdepth 3 -name "$(basename "$hk")" 2>/dev/null); do  # chained hook (rm_chain_*)
        grep -q -E 'stn_pin_keepout|pinko_add|_pk\.tcl' "$hf" && ECO_PK=1
      done
    done
  fi
fi
# MACRO-EDGE VIA GUARD (2026-10-13): a route whose hooks sourced physical/common_flow/macro_edge_via_guard.tcl gets the
# same guard around the ECO's GRT/DRT (hold_eco.tcl OT_ECO_MEG, with the route's OT_MEG_* knobs).  ECO_MEG=0 opts out.
if [ -z "${ECO_MEG:-}" ]; then
  ECO_MEG=0
  if [ -f "$RCFG" ]; then
    for hk in $(sed -n 's/^export \(PRE_GLOBAL_ROUTE_TCL\|POST_DETAIL_ROUTE_TCL\) *= *//p' "$RCFG"); do
      for hf in $(find "$(dirname "$RCFG")/.." -maxdepth 3 -name "$(basename "$hk")" 2>/dev/null); do
        if grep -q 'macro_edge_via_guard' "$hf"; then ECO_MEG=1; fi
        for sf in $(grep -o '/src/[^ ;"]*\.tcl' "$hf" | sed 's|^/src/||'); do   # one level down: a kit wrapper that sources it
          if [ -f "$PWD/$sf" ] && grep -q 'macro_edge_via_guard' "$PWD/$sf"; then ECO_MEG=1; fi
        done
      done
    done
  fi
fi
echo "OT_ECO macro-edge via guard in the re-route: $ECO_MEG" | tee -a "$OUT/eco.log"
PK_ENV=(-e OT_ECO_PK=$ECO_PK -e OT_ECO_MEG=$ECO_MEG)
if [ "$ECO_MEG" = 1 ] && [ -f "$RCFG" ]; then
  for v in OT_MEG_DEPTH_UM OT_MEG_PIN_UM; do
    x=$(sed -n "s/^export $v *= *//p" "$RCFG" | tail -1)
    if [ -n "$x" ]; then PK_ENV+=(-e "$v=$x"); fi
  done
fi
if [ "$ECO_PK" = 1 ]; then
  for v in OT_PK_FRAC OT_PK_HALO OT_PK_FACES; do
    x=$( [ -f "$RCFG" ] && sed -n "s/^export $v *= *//p" "$RCFG" | tail -1 )
    [ -n "$x" ] && PK_ENV+=(-e "$v=$x")
  done
  PK_ENV+=(-e OT_PK_ABOVE_ONLY=1)
fi
echo "OT_ECO face-pin keepout in the re-route: $ECO_PK (route config: $RCFG)" | tee -a "$OUT/eco.log"
export SDC_NAME=${SDC_NAME:-6_final.sdc}
[ -f "$OB/$SDC_NAME" ] || { echo "sign-off SDC $OB/$SDC_NAME missing"; exit 2; }
SPS=""; for p in ${SETUP_POST_SDC:-}; do SPS="$SPS /src/$p"; done
# CORNER-STA (drive-1010 2026-10-10): a pre option-B source snapshot has a corner_sta.py without setup_tt; the ECO then
# failed every time ("corner_sta without setup_tt", vtswap exit 8 -> combo "no vtswap base" rc=3, selt_q r6 cx-f5-hm0).
# Sign-off STA is the loop's, like the verdict re-STA: use the shipped helper copy when the snapshot's lacks setup_tt.
CSTA=tools/w18/corner_sta.py; grep -q setup_tt "$CSTA" 2>/dev/null || { [ -f "$(dirname "$0")/corner_sta.py" ] && CSTA="$(cd "$(dirname "$0")" && pwd)/corner_sta.py"; }
SN=""; grep -q -- "--sdc-name" "$CSTA" && SN="--sdc-name $SDC_NAME"
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
# LEAST-BAD (2026-10-13, ot_qkvd_sbuf_m5-m5: both passes finished at FF -3.97 / -1.35 with DRC 4, every score -1e9, so the
# script ended "no ECO pass produced a result" and the numbers were lost): a pass that finished its sign-off but is not
# clean is remembered by rank (worst slack under the acceptance line - 1000 per DRC); when no pass is clean its
# result.json / corner_sta.json are still written to <out> (chosen = least_bad) and the script exits 9 as before.
lb=""; lbrank=-1e18
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
  [ $FAILED = 0 ] || { [ -n "$best$lb" ] && break; exit 9; }   # a later pass failing keeps the best earlier pass
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
           -e OT_DRV_MAX_WIRE=${DRV_MAX_WIRE:-0} "${PK_ENV[@]}" "${NATIVE_NORMALIZE_ENV[@]}" -e ECTL_ECO_INPUT_ODB=/in/$CUR_DB)
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
  # a route with wire above its layer cap is refused by hold_eco.tcl (it used to abort OpenROAD: rc=9 with no reason)
  if grep -q "OT_ECO layer_cap_leak" $L; then grep "OT_ECO layer_cap_leak" $L | tee -a $OUT/eco.log; echo "ECO refused: route violates its layer cap (not an ECO candidate; regenerate the kit and re-route)"; exit 11; fi
  grep -q "OT_ECO done" $L || { echo "ECO pass $k failed (no OT_ECO done)"; tail -20 $L; [ -n "$best$lb" ] && break; exit 9; }
  seed_sdc   # the ECO may have rewritten the base's SDC
  python3 $CSTA $CS_ARGS $SN --orfs-dir $P/orfs --output $P/corner_sta.json > $P/corner.log 2>&1 \
    || { echo "corner_sta failed"; tail $P/corner.log; exit 8; }
  if [ -n "${SETUP_POST_SDC:-}" ]; then   # setup corners re-timed with the measured neighbour clock (the route's own merge)
    python3 $CSTA $CS_ARGS $(for q in $SETUP_POST_SDC; do echo -n " --post-sdc $q"; done) $SN \
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
r['rank'] = (min(r['ss_ps'] - acc_ss, r['ff_ps'] - acc_ff) - 1000.0 * (r['drc'] if r['drc'] is not None else 1000)
             - (1e6 if r['errors'] else 0)) if ok else -1e12
json.dump(r, open(f'{p}/result.json', 'w'), indent=1); print('OT_PASS_RESULT', json.dumps(r))
PY
  cat $P/result.json >> $OUT/eco.log
  sc=$(python3 -c "import json;print(json.load(open('$P/result.json'))['score'])")
  # Only acceptance-clean passes can become the installed best. Negative
  # scores remain in lb as failure evidence and must return exit 9.
  if python3 -c "import sys; sys.exit(0 if $sc >= 0 and $sc > $bestscore else 1)"; then best=$P; bestscore=$sc; fi
  rk=$(python3 -c "import json;print(json.load(open('$P/result.json'))['rank'])")
  if python3 -c "import sys; sys.exit(0 if $rk > $lbrank else 1)"; then lb=$P; lbrank=$rk; fi
  # done when the routed result meets the post-route goal (FF >= HM), not merely the acceptance line
  python3 -c "import json,sys; r=json.load(open('$P/result.json')); sys.exit(0 if r['score'] >= 0 and r['ff_ps'] >= float('${HM:-18}') else 1)" && break
  # the next pass restarts from the ORIGINAL route (its GRT guides intact) with a larger allowance: chaining passes on an
  # ECO'd db hit DRT-0218 'Guide is not connected to design' (capt_x, hfd_svc_SE_s6 pass 2)
  PREV_FF=$(python3 -c "import json;print(json.load(open('$P/result.json'))['ff_ps'])")
done
if [ -z "$best" ]; then
  [ -n "$lb" ] || { echo "no ECO pass produced a result"; exit 9; }
  cp $lb/corner_sta.json $OUT/corner_sta.json
  python3 -c "import json,sys; r=json.load(open(sys.argv[1])); r['chosen']='least_bad'; json.dump(r, open(sys.argv[2],'w'), indent=1)" $lb/result.json $OUT/result.json
  echo "OT_ECO no clean pass; least-bad $(basename $lb) kept as evidence (not installed)" | tee -a $OUT/eco.log
  cat $OUT/result.json
  exit 9
fi
ln -sfn $(basename $best)/orfs $OUT/orfs
cp $best/corner_sta.json $OUT/corner_sta.json
cp $best/result.json $OUT/result.json
echo "OT_ECO chosen $(basename $best)" | tee -a $OUT/eco.log
grep "Number of violations" $best/eco_*.log | tail -1 >> $OUT/eco.log || true
cat $OUT/result.json
