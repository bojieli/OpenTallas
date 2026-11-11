#!/bin/bash
# DIE-QC-97 SU-LAT-1 (11-11): give back the s16 +1 pin cycle on the 12 su_l0 x_su_c lanes, on s19 (SU-CH-1).
#   derive_lat1.sh HEAD_PLAN(s19) SIDECAR_IN(s19, 0cd376957c97) OUTDIR MEAS_DIR(derive_rs1/meas)
# 1. lane3.py: x_su_c_i gets N=3 stations in every su_l0 type. It fails closed if any chain cannot fit:
#    channel chains by the kit's even spacing, L chains by the measured kit-knee need. Lanes go fixed_cycles 4 -> 3.
# 2. remap24 / merge24 / collector_reattach --sidecar / fixreach / anchor_su (as derive_ch1.sh).
# 3. checks.  The latency table (latency.lanes, the lanes' RTL LAT_* params) is NOT touched: by convention its cycles =
#    plan lane_latency - fixed (all 259 G0 "table says" rows on this die are exactly that), the fixed cycles being the
#    type kits' stations.  These lanes keep table 4 (= plan 7 - fixed 3).  Rewriting a row to 7 fails the strict bind
#    (R8_STALE: bound 7 vs as-built 4).
# PINFACE_SRC: a tool tree with KIT-CHAN-1 (main >= 631d10d72180), with tools/die_plan as REAL files.
set -euo pipefail
cd /tmp
W=/srv/opentallas-scratch2/claude/dq97/sul0f; S=${PINFACE_SRC:?tool tree with KIT-CHAN-1}; RA=$S/tools/die_plan
HEAD=$1; SC=$2; O=$3; MD=$4; HERE=$(cd "$(dirname "$0")" && pwd)
SU0="sle_su_l0__cl086d85ba sle_su_l0__cl7a55c676 slw_su_l0__cl1a1c1f8f slw_su_l0__cl1e5219ea slw_su_l0__cl76fb247e"
SU1="sle_su_l1__cl5ea486db sle_su_l1__clc6d66f5b slw_su_l1__cla2a78701 slw_su_l1__clcc9d0155"
mkdir -p $O/rmp
python3 -I -c "import json,sys; open(sys.argv[2],'w').write(json.dumps(json.load(open(sys.argv[1])))+'\n')" $HEAD $O/head.json
python3 -I $HERE/lane3.py $S $O/head.json $O/cand1.json $O/lane3_rep.json $MD
for t in $SU0; do ( RM_TYPES=$t timeout 7200 python3 -I $W/remap24.py $S $RA $O/head.json $O/cand1.json $O/rmp/$t.json $O/rmp/$t.rep.json > $O/rmp/$t.out 2>&1 || echo "REMAP FAIL $t" ) & done; wait
for t in $SU1; do ln -sf $O/head.json $O/rmp/$t.json; done
python3 -I $W/merge24.py $O/head.json $O/cand1.json $O/rmp $O/cand2.json
python3 -I $RA/collector_reattach.py $O/head.json $O/cand2.json $O/cand3.json $O/reattach.json --sidecar $SC $O/sidecar.json
python3 -I $W/fixreach.py $S $O/cand3.json $O/cand4.json $O/fixreach.json $(for t in $SU0; do echo $t=$O/rmp/$t.json.$t.tree.json; done)
python3 -I $W/anchor_su.py $S $RA $O/head.json $O/cand4.json $O/cand5.json $(for t in $SU0; do echo $t=$O/rmp/$t.json.$t.tree.json; done)
python3 -I -c "import json,sys; open(sys.argv[2],'w').write(json.dumps(json.load(open(sys.argv[1])),indent=1,ensure_ascii=False))" $O/cand5.json $O/cand.json
{ date -u; sha256sum $O/cand.json $O/sidecar.json
  (cd $S && python3 -I $W/val.py $S $O/cand.json)
  python3 -I $W/gate.py $S $O/cand.json
  python3 -I $W/chkreach.py $S $O/cand.json | tail -1
  python3 -I /srv/opentallas-scratch2/claude/dq97/stm/rstchk.py $S $O/rstchk.json $O/cand.json | grep -E 'with missing|BAD'
} > $O/SUMMARY.txt 2>&1
cat $O/SUMMARY.txt
