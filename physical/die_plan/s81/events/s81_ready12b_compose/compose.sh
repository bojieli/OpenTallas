#!/bin/bash
# S81 ready12b-A compose (S81-LEAF-FLOOR-2 for DIE-S81-88, 11-12).  One stage per step, each idempotent (an output
# whose receipt names the same input sha is kept), receipt per stage in $R/rN_*.json.  Skipped stages: receipt with why.
set -u
R=/srv/opentallas-scratch2/claude/s81-leaf-floor-2/r12b; T=$R/tools/die_plan; cd $R
BASE=/srv/opentallas-scratch2/claude/s87bind/plan_ready12ng.json
sha() { sha256sum < "$1" | cut -c1-64; }
fresh() {  # fresh OUT RECEIPT IN : 0 if OUT exists and its receipt names IN's sha
    [ -f "$1" ] && [ -f "$2" ] && python3 -I -c "import json,sys; r=json.load(open('$2')); sys.exit(0 if r.get('in_sha256')=='$(sha $3)' and r.get('out_sha256')=='$(sha $1)' else 1)"
}
skip() { python3 -I -c "import json; json.dump(dict(stage='$1', skipped=True, why='''$2'''), open('$R/$3','w'), indent=1)"; echo "SKIP $1: $2"; }
echo "BASE $(sha $BASE | cut -c1-12)"
# 1 LF-CS direct (cs rows -> 0 registers; leaf depths themselves are the die-netlist stage, not a plan edit)
fresh s1_lfcs.json r1_lfcs.json $BASE || { python3 -I $T/stage_leaf_cs_direct.py $BASE s1_lfcs.json --constraints lf4_reach_cs.json && \
    python3 -I receipt.py lfcs $BASE s1_lfcs.json r1_lfcs.json tool=stage_leaf_cs_direct.py@origin/s81-lfcs-depth-gate constraints=lf4_reach_cs.json; } || exit 11
# 2 TAPWIN-FLOOR (origin/claude/die-s81-88-tapwin-1112 @f2048007ab19)
fresh s2_tapwin.json r2_tapwin.json s1_lfcs.json || { python3 -I $T/stage_s81_tapwin_floor.py s1_lfcs.json s2_tapwin.json \
    --kitwin /srv/opentallas-scratch2/claude/window-s81-1/in/kitwin_auto_r7b_4cf8fb2f1479.json > s2_tapwin.log 2>&1 && \
    python3 -I receipt.py tapwin s1_lfcs.json s2_tapwin.json r2_tapwin.json tool=stage_s81_tapwin_floor.py@f2048007ab19; } || { tail -5 s2_tapwin.log; exit 12; }
# 3 svc_lo_dsdv_svc_rs__t7 hbm_i0 band rect (land-ring-2 fixplan.py)
fresh s3_band.json r3_band.json s2_tapwin.json || { python3 -I /srv/opentallas-scratch2/claude/land-ring-2/s81/fixplan.py s2_tapwin.json s3_band.json && \
    python3 -I receipt.py band s2_tapwin.json s3_band.json r3_band.json tool=land-ring-2/s81/fixplan.py; } || exit 13
# 4 REACH-FIX-2 (plan_s81_r12ng: base 77cad171c6ee -> 79e22ea61177, cap 800), carried as a fail-closed patch
RF=/srv/opentallas-scratch2/claude/reach-fix-2/plan_s81_r12ng/plan_rf.json
[ -f rf2.patch.json ] || python3 -I plan_patch.py diff $BASE $RF rf2.patch.json || exit 14
fresh s4_rf2.json r4_rf2.json s3_band.json || { python3 -I plan_patch.py apply s3_band.json rf2.patch.json s4_rf2.json --receipt r4_rf2_patch.json && \
    python3 -I receipt.py reachfix2 s3_band.json s4_rf2.json r4_rf2.json tool=reach-fix-2/plan_rf.json@79e22ea61177 patch=rf2.patch.json; } || exit 14
skip xtier "plan_xtd9 (epyc9 x-tier-otc-kit/src, f97e5075c37c, 45 MB) is on an older plan lineage, not ready12ng 77cad171c6ee; no xtd10 exists; no stage script (m89_form.py + p_*.py chain): carrying it needs the X-TIER owner to re-stage form (d) on ready12ng" r5_xtier.json
skip diereview "claude/s81-diereview-1112 @ee331af70c events/s81_diereview_1112 holds the review + resign_batch_ready12b.tsv table, no plan-edit stage; used as the re-sign list input" r6_diereview.json
skip lf4 "LF4 street remainder + core moves not ready (ready12b-B)" r7_lf4.json
cp -f s4_rf2.json plan_ready12b_A.json
echo "READY12B_A $(sha plan_ready12b_A.json | cut -c1-12)"
