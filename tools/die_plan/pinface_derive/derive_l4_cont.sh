#!/bin/bash
# DIE-QC-97 SUL0-PINFACE-1: lane pin-face register form, re-runnable from core positions.
#   derive_pinface.sh HEAD_PLAN SIDECAR_IN OUTDIR [STRIP_REP|-]
# HEAD_PLAN: the QC plan with the su_l0/su_l1 hard cores where CPL-QC-SU put them.  If its su types still carry
#   pin-face chains (cand23d / cand24), STRIP_REP is the mk_cand report that added them (default: cand23d_rep.json);
#   "-" = the plan has none.
# PINFACE_SRC (env): tool tree for every step incl. reset_anchor / collector_reattach / schema (default srcc + ra + cra + mainm);
#   set it to the tree the strict bind uses so the solved relay trees and anchors are the ones the bind builds.
# SIDECAR_IN: the asbuilt clock_landing_table sidecar of HEAD_PLAN (collector sources the strict bind reads).
# Steps (all plan-level, epyc7, no kit build): strip old chains -> measure every lane pin face per type from the plan's
#   core positions + the type kit's bound RTL / io.tcl (knee 400 um, macro-clear L routes, cland q-pin starts) ->
#   mk_cand (one latency per bus, lane fixed_cycles) -> station sinks for sink_bins types -> site-anchored relay
#   remap (reset_anchor, keeps depth via reset.wavefront_min_depth) -> merge onto HEAD (non-su byte-same) ->
#   collector_reattach --sidecar (<= 405) -> stage reach re-pick (<= 405) -> checks (schema main+gate, gate,
#   reach, rstchk); on an anchored head the su reset_tree_anchor is re-recorded on the solved trees.  Output: OUTDIR/cand.json, OUTDIR/sidecar.json, OUTDIR/SUMMARY.txt.
set -euo pipefail
cd /tmp
W=/srv/opentallas-scratch2/claude/dq97/sul0f; S=${PINFACE_SRC:-$W/srcc}; RA=${PINFACE_SRC:+$S/tools/die_plan}; RA=${RA:-$W/ra}; CRA=${PINFACE_SRC:+$S/tools/die_plan}; CRA=${CRA:-$W/cra}; VS=${PINFACE_SRC:-$W/mainm}; C=/srv/opentallas-scratch2/claude/dq97/cls2/cores
HEAD=$1; SC=$2; O=$3; REP=${4:-$W/cand23d_rep.json}
SU="sle_su_l0__cl086d85ba sle_su_l0__cl7a55c676 sle_su_l1__cl5ea486db sle_su_l1__clc6d66f5b slw_su_l0__cl1a1c1f8f slw_su_l0__cl1e5219ea slw_su_l0__cl76fb247e slw_su_l1__cla2a78701 slw_su_l1__clcc9d0155"
python3 -I $W/merge24.py $HEAD $O/cand1.json $O/rmp $O/cand2.json
python3 -I $CRA/collector_reattach.py $HEAD $O/cand2.json $O/cand3.json $O/reattach.json --sidecar $SC $O/sidecar.json
python3 -I $W/fixreach.py $S $O/cand3.json $O/cand4.json $O/fixreach.json $(for t in $SU; do echo $t=$O/rmp/$t.json.$t.tree.json; done)
# anchored head: the su anchors are re-recorded on the solved trees (the head's describe the old trees)
python3 -I $W/anchor_su.py $S $RA $HEAD $O/cand4.json $O/cand.json $(for t in $SU; do echo $t=$O/rmp/$t.json.$t.tree.json; done)
{ date -u; sha256sum $O/cand.json $O/sidecar.json
  (cd $VS && python3 -I $W/val.py $VS $O/cand.json)
  python3 -I $W/gate.py $S $O/cand.json
  python3 -I $W/chkreach.py $S $O/cand.json | tail -1
  python3 -I /srv/opentallas-scratch2/claude/dq97/stm/rstchk.py $S $O/rstchk.json $O/cand.json | grep -E 'with missing|BAD'
} > $O/SUMMARY.txt 2>&1
cat $O/SUMMARY.txt
