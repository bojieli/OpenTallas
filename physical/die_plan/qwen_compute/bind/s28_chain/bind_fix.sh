#!/bin/bash
# QC-S28-BIND deterministic fix chain on ANY composed QC s28 plan (re-run it on the final plan after LAND / snap_lattice):
#   (b) fix_h_straps.py    cbx_q10 *_h parent_id_straps derived from the event elaboration (ELAB/asbuilt.json)
#   (c) reset_pad.sh       reset trees pad, never shorten, vs REF (pre-HF-1c s28a_bc)
#   (c) reset_repick.sh    TAPS stage_r rule on the anchors of zz_c1_taps (START same depth nearest stage, local copy
#                          depth law by tree-depth change, anchors re-recorded)
#   tap_ident.sh           forwarded clock source identity by tap location vs TI_REF, guarded re-point
#   (d) reach5.sh fix      optional (RF=1): reach_fix.py class 5 with --ref-plan REF
#   strict bind (--all-gaps) -> local_copy_fix.py on the measured EMIT copy-depth gaps -> bind again (<= 3 rounds)
#   lane_proof_all.py on the final bind (delivered latency == bind_latency on every lane)
#   (a) land_r8_derive derive from the clean-plan bus_groups -> final strict bind (no --all-gaps) -> land_r8_derive check
# usage: bind_fix.sh PLAN_IN SIDECAR TAG [ELAB_DIR]
set -u; B=/srv/opentallas-scratch2/claude/qc-s28-hf1c/bind; E=${EVENT_TREE:-/srv/opentallas-scratch2/claude/wt/qc-s28-event}
RT=physical/die_plan/qwen_compute/qc_start_1106/runtime; POR=physical/die_plan/qwen_compute/plan_of_record; REF=$B/in/zz_s28a_bc.json
PL=$1; SIDE=$2; TAG=$3; G=${4:-$B/bind_c6b_base}; W=$B/work/$TAG; mkdir -p $W; L=$W/chain.log
log() { echo "$*" >> $L; }
# clock_merge sibling of the INPUT plan follows every intermediate plan of the chain (run_bind.sh / cm_inject.py)
[ -z "${CM_FILE:-}" ] && [ -e "${PL%.json}.clock_merge.json" ] && export CM_FILE=${PL%.json}.clock_merge.json
[ -z "${KP_FILE:-}" ] && [ -e "${PL%.json}.kit_pricing.json" ] && export KP_FILE=${PL%.json}.kit_pricing.json
[ "${REQUIRE_KP:-0}" = 1 ] && [ -z "${KP_FILE:-}" ] && { echo "REQUIRE_KP=1 but no ${PL%.json}.kit_pricing.json" > $L; exit 2; }
[ "${REQUIRE_CM:-0}" = 1 ] && [ -z "${CM_FILE:-}" ] && { echo "REQUIRE_CM=1 but no ${PL%.json}.clock_merge.json" > $L; exit 2; }
echo "FIX $TAG start $(date) plan=$(sha256sum $PL|cut -c1-12) side=$(sha256sum $SIDE|cut -c1-12) cm_file=${CM_FILE:-none} kp_file=${KP_FILE:-none} tree=$(cd $E && git rev-parse --short=12 HEAD)" > $L
python3 -I $B/fix_h_straps.py $PL $W/p1_straps.json $G/asbuilt.json $W/straps_report.json >> $L 2>&1 || { log "STRAPS FAIL"; exit 3; }
bash $B/reset_pad.sh $W/p1_straps.json $REF $W/p2_pad.json $TAG >> $L 2>&1 || { log "PAD FAIL"; exit 4; }
cp $B/work/reset_pad_$TAG.json $B/work/eq_reset_pad_$TAG.tsv $W/; grep RESET_PAD $B/work/reset_pad_$TAG.log >> $L
bash $B/reset_repick.sh $W/p2_pad.json $W/p3_repick.json $TAG >> $L 2>&1 || { log "REPICK FAIL"; exit 5; }
cp $B/work/reset_repick_$TAG.json $B/work/eq_reset_repick_$TAG.tsv $W/; grep REPICK $B/work/reset_repick_$TAG.log >> $L
# tap identity (tap_ident.py): derived taps renumber on geometry moves; forwarded source_clock_port kept by LOCATION vs
# TI_REF (default the pre-RESID c6b), guarded re-point (<= 1 pitch, hop never crosses 405), EQ row per re-point
bash $B/tap_ident.sh ${TI_REF:-$B/in/zz_c6b_fix.json} $W/p3_repick.json $W/p3b_taps.json $TAG > /dev/null 2>&1 || { grep "TAP_IDENT" $B/work/tap_ident_$TAG.log >> $L; log "TAP_IDENT FAIL"; exit 9; }
cp $B/work/tap_ident_$TAG.json $B/work/eq_tap_ident_$TAG.tsv $W/; grep "^TAP_IDENT" $B/work/tap_ident_$TAG.log | cut -c1-300 >> $L
FIN=$W/p3b_taps.json
if [ "${RF:-0}" = 1 ]; then
  bash $B/reach5.sh fix $FIN $REF $TAG >> $L 2>&1; grep -q "^RC=0" $B/reach_$TAG/fix.log || { log "REACH FAIL"; exit 6; }
  cp $B/reach_$TAG/plan_fix.json $W/p4_reach.json; FIN=$W/p4_reach.json
fi
n=0
while :; do
  ALLGAPS=1 bash $B/run_bind.sh ${TAG}_g$n $FIN $SIDE $G >> $L 2>&1
  # gaps from bind_report.json errors (the log may print only the first error class)
  python3 -I -c "import json,sys;sys.exit(0 if any(': consumer ' in str(e) and '!= copy depth' in str(e) for e in json.load(open(sys.argv[1]))['errors']) else 1)" $B/bind_${TAG}_g$n/bind_report.json || break
  [ $n -ge 3 ] && { log "LOCAL COPY LOOP did not converge"; exit 7; }
  P=$E/$POR/zz_lc_in_$TAG.json; O=$E/$POR/zz_lc_out_$TAG.json; rm -f $P $O; cp $FIN $P
  (cd $E && python3 -I $B/local_copy_fix.py $POR/zz_lc_in_$TAG.json $B/bind_${TAG}_g$n/bind_report.json --out $POR/zz_lc_out_$TAG.json \
     --report $W/local_copy_$n.json --eq $W/eq_local_copy_$n.tsv) >> $L 2>&1 || { log "LOCAL COPY FIX FAIL"; exit 8; }
  n=$((n+1)); cp $O $W/p5_lc$n.json; FIN=$W/p5_lc$n.json; rm -f $P $O
done
cp $FIN $W/plan_final.json; log "plan_final=$(sha256sum $W/plan_final.json|cut -c1-12)"
# r8 is derived ONLY from a bind whose remaining errors are r8-class (r8_gate.py: R8_STALE, PARAM_REGEN "would need a
# pad", which reads the R8 landings and clears only after the derive); never from a bind that failed for other reasons.
# ONE derive, then the strict final bind: an r8-class error left there fails the chain (BIND_RC != 0).
python3 -I $B/r8_gate.py $B/bind_${TAG}_g$n/bind_report.json > $W/r8_gate.log 2>&1; grc=$?; log "R8_GATE $(head -1 $W/r8_gate.log)"
if [ "$grc" != 0 ]; then
  log "OTHER ERRORS in bind_${TAG}_g$n (not r8-class / local copy): r8 not derived; chain stops"
  tail -n +2 $W/r8_gate.log >> $L
  log "CHAIN_DONE $TAG final_bind=${TAG}_g$n BIND_RC=1 (other errors)"; exit 10
fi
cp $E/$RT/r8_sw2.json $W/r8_sw2_before.json
s0=$(sha256sum < $E/$RT/r8_sw2.json | cut -c1-12)
(cd $E && python3 -I tools/die_plan/land_r8_derive.py derive $POR/zz_bind_${TAG}_g$n.json $B/bind_${TAG}_g$n/bus_groups.json --like $RT/r8_sw2.json --out $RT/r8_sw2.json --json $W/r8_derive.json | cut -c1-200) >> $L 2>&1
s1=$(sha256sum < $E/$RT/r8_sw2.json | cut -c1-12); log "r8 $s0 -> $s1"
bash $B/run_bind.sh $TAG $W/plan_final.json $SIDE $G >> $L 2>&1
(cd $E && python3 -I tools/die_plan/land_r8_derive.py check $POR/zz_bind_$TAG.json $B/bind_$TAG/bus_groups.json --table $RT/r8_sw2.json --json $W/r8_check.json > $W/r8_check.log 2>&1; echo "R8_CHECK_RC=$?") >> $L
# as-built lane proof (COORD 11-12): bound RTL + kit_istations --apply on scratch copies, every lane; mismatch/unmeasured fail
(cd $E && python3 -I $B/lane_proof_all.py $B/bind_$TAG $POR/zz_bind_$TAG.json $W/lane_proof $B/bind_$TAG/lane_proof.tsv --jobs 8 > $W/lane_proof.log 2>&1; echo "LANE_PROOF_RC=$?") >> $L
grep "^LANE_PROOF" $W/lane_proof.log | cut -c1-300 >> $L
log "CHAIN_DONE $TAG final_bind=$TAG $(grep ^BIND_RC $B/bind_$TAG.log) $(grep -o "LANE_PROOF_RC=[0-9]*" $L | tail -1)"
