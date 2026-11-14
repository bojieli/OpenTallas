#!/bin/bash
# DIE-QC-100 reusable QC reset pipeline (the reset part of bind_fix.sh, without the bind), for ANY composed QC plan
# (event plans, form lanes' plans that move cores).  Run it BEFORE the strict (re-)bind; bind the PLAN_OUT it writes.
#   (b) fix_h_straps.py  cbx_q10 *_h parent_id_straps from the event elaboration     (STRAPS=0 skips)
#   (c) reset_pad.sh x2  reset trees pad, never shorten, vs PAD_REF then vs REPICK_BASE (the anchor base) -> no "got shallower"
#   (c) reset_repick.sh  START stage raw_reset same depth nearest relay; local-copy depth law; anchors re-recorded
#   tap_ident.sh         forwarded source_clock_port kept by LOCATION vs TI_REF, guarded re-point (FINAL-first)
#   (d) reach5.sh fix    optional RF=1: reach_fix class 5 (reset hops > 405) with --ref-plan PAD_REF
#   reset_reach.py       measure before / after: refs > 405 um and refs naming no relay of the solved tree
# usage: reset_steps.sh PLAN_IN PLAN_OUT TAG
# env:   EVENT_TREE  tree with tools/die_plan (default wt/qc-s28-event2, has the SU lpad fix 3df9d1b1e0)
#        PAD_REF (in/zz_s28a_bc d24fc85ccaad)  REPICK_BASE (in/zz_c1_taps 67b0bf06d8dc)  TI_REF (in/zz_c6b_fix d80080a8d310)
#        ELAB (bind_c6b_base: asbuilt.json for straps)  RF=1  STRAPS=0
# out:   work/rs_TAG/{chain.log, p*.json, eq_*.tsv, reset_reach_{in,out}.json}; exit 0 only if every step passed and
#        the after-measure is no worse than the input (exit 20 otherwise).  reset_reach is the TAPS solved-tree measure,
#        informational: acceptance is the strict bind (0 RESET_ANCHOR / EMIT copy-depth / reset errors) on PLAN_OUT.
# then:  bind PLAN_OUT (run_bind.sh / rebind_qc.sh), local_copy_fix on EMIT copy-depth gaps, r8 derive (see bind_fix.sh).
set -u; cd /
B=/srv/opentallas-scratch2/claude/qc-s28-hf1c/bind
export EVENT_TREE=${EVENT_TREE:-/srv/opentallas-scratch2/claude/wt/qc-s28-event2}
[ $# -eq 3 ] || { sed -n 2,17p "$0"; exit 2; }
PL=$(readlink -f "$1"); OUT=$2; TAG=rs_$3; W=$B/work/$TAG; mkdir -p $W; L=$W/chain.log
PAD_REF=${PAD_REF:-$B/in/zz_s28a_bc.json}; REPICK_BASE=${REPICK_BASE:-$B/in/zz_c1_taps.json}
TI_REF=${TI_REF:-$B/in/zz_c6b_fix.json}; ELAB=${ELAB:-$B/bind_c6b_base}
log() { echo "$*" >> $L; }
sha() { sha256sum < "$1" | cut -c1-12; }
echo "RESET_STEPS $TAG start $(date) host=$(hostname) plan=$(sha $PL) tree=$EVENT_TREE pad_ref=$(sha $PAD_REF) repick_base=$(sha $REPICK_BASE) ti_ref=$(sha $TI_REF)" > $L
measure() { bash $B/reset_reach.sh ${TAG}_$2 $1; cp $B/work/reset_reach_${TAG}_$2.json $W/reset_reach_$2.json 2>/dev/null
  python3 -I -c 'import json,sys
d=json.load(open(sys.argv[1]))[0]; t={k:v for k,v in d.items() if k not in ("plan","types")}
print("RESET_REACH", sys.argv[2], json.dumps(t), "types_bad", len(d["types"]))' $W/reset_reach_$2.json $2 >> $L 2>&1 || tail -3 $B/work/reset_reach_${TAG}_$2.log >> $L; }
measure $PL in
cur=$PL
if [ "${STRAPS:-1}" = 1 ]; then
  python3 -I $B/fix_h_straps.py $cur $W/p1_straps.json $ELAB/asbuilt.json $W/straps_report.json >> $L 2>&1 || { log "STRAPS FAIL"; exit 3; }
  cur=$W/p1_straps.json
fi
bash $B/reset_pad.sh $cur $PAD_REF $W/p2_pad.json $TAG >> $L 2>&1 || { tail -5 $B/work/reset_pad_$TAG.log >> $L; log "PAD FAIL"; exit 4; }
cp $B/work/reset_pad_$TAG.json $B/work/eq_reset_pad_$TAG.tsv $W/ 2>/dev/null; grep RESET_PAD $B/work/reset_pad_$TAG.log >> $L
# second pad vs the ANCHOR base (REPICK_BASE): the reset_tree_anchor records were made there, and on some types it is deeper
# than PAD_REF (cbn_q00__cldbcda913: s28a_bc 10, c1_taps 11 -> repick "got shallower 11 -> 10").  Pad only, never shorten.
bash $B/reset_pad.sh $W/p2_pad.json $REPICK_BASE $W/p2b_pad.json ${TAG}b >> $L 2>&1 || { tail -5 $B/work/reset_pad_${TAG}b.log >> $L; log "PAD(anchor base) FAIL"; exit 4; }
cp $B/work/reset_pad_${TAG}b.json $B/work/eq_reset_pad_${TAG}b.tsv $W/ 2>/dev/null; grep RESET_PAD $B/work/reset_pad_${TAG}b.log | sed 's/^/anchor-base /' >> $L
bash $B/reset_repick.sh $W/p2b_pad.json $W/p3_repick.json $TAG $REPICK_BASE >> $L 2>&1 || { tail -5 $B/work/reset_repick_$TAG.log >> $L; log "REPICK FAIL"; exit 5; }
cp $B/work/reset_repick_$TAG.json $B/work/eq_reset_repick_$TAG.tsv $W/ 2>/dev/null; grep REPICK $B/work/reset_repick_$TAG.log >> $L
bash $B/tap_ident.sh $TI_REF $W/p3_repick.json $W/p4_taps.json $TAG > /dev/null 2>&1 || { grep TAP_IDENT $B/work/tap_ident_$TAG.log | cut -c1-300 >> $L; log "TAP_IDENT FAIL"; exit 9; }
cp $B/work/tap_ident_$TAG.json $B/work/eq_tap_ident_$TAG.tsv $W/ 2>/dev/null; grep "^TAP_IDENT" $B/work/tap_ident_$TAG.log | cut -c1-300 >> $L
FIN=$W/p4_taps.json
if [ "${RF:-0}" = 1 ]; then
  bash $B/reach5.sh fix $FIN $PAD_REF $TAG >> $L 2>&1; grep -q "^RC=0" $B/reach_$TAG/fix.log || { log "REACH FAIL"; exit 6; }
  cp $B/reach_$TAG/plan_fix.json $W/p5_reach.json; FIN=$W/p5_reach.json
fi
cp $FIN "$OUT"; measure "$OUT" out
log "RESET_STEPS_DONE $TAG out=$(sha $OUT) $(date)"
python3 -I -c 'import json,sys
f=lambda x:json.load(open(x))[0]; i,o=f(sys.argv[1]),f(sys.argv[2])
k=("start_far","local_far","start_missing","local_missing"); w=[x for x in k if o[x]>i[x]]
print("RESET_REACH_DELTA", {x:o[x]-i[x] for x in k}); sys.exit(20 if w else 0)' $W/reset_reach_in.json $W/reset_reach_out.json >> $L 2>&1 || { log "RESET_REACH worse than input (see reset_reach_{in,out}.json)"; exit 20; }
