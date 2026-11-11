#!/bin/bash
# DIE-QC-97 SU-CH-1 (11-11): su_l0 channel leg order on the s18 plan (KIT-CHAN-1 users), plan level, epyc7.
#   derive_ch1.sh HEAD_PLAN SIDECAR_IN OUTDIR [FACE:LO:HI=W:8:120]
# 1. to_channel.py: along_first su_l0 core chains -> leg_order channel + channel_um when the channel Z path has the L
#    route's exact per-bit length (stations, hops, lanes and pin cycles unchanged).
# 2. Station sites move, so the reset relay trees renumber: remap24 records the anchors on HEAD's trees and resolves
#    them on the new ones, per su_l0 type.  merge24 (su_l1 types from HEAD) -> collector_reattach --sidecar ->
#    fixreach -> anchor_su re-records clock.reset_tree_anchor on the solved trees.
# 3. checks: schema (KIT-CHAN-1 tools), gate, chkreach, rstchk.
# PINFACE_SRC: a tool tree with KIT-CHAN-1 (main >= 631d10d72180), with tools/die_plan as REAL files (a symlinked module
# puts its realpath directory first on sys.path and the old schema is imported).  The helper scripts (remap24 / merge24 /
# fixreach / anchor_su / val / gate / chkreach) are the derive_pinface.sh ones in $W.
set -euo pipefail
cd /tmp
W=/srv/opentallas-scratch2/claude/dq97/sul0f; S=${PINFACE_SRC:?tool tree with KIT-CHAN-1}; RA=$S/tools/die_plan
HEAD=$1; SC=$2; O=$3; CH=${4:-W:8:120}; HERE=$(cd "$(dirname "$0")" && pwd)
SU0="sle_su_l0__cl086d85ba sle_su_l0__cl7a55c676 slw_su_l0__cl1a1c1f8f slw_su_l0__cl1e5219ea slw_su_l0__cl76fb247e"
SU1="sle_su_l1__cl5ea486db sle_su_l1__clc6d66f5b slw_su_l1__cla2a78701 slw_su_l1__clcc9d0155"
mkdir -p $O/rmp
# the helpers need a json.dumps style they know: HEAD is re-dumped plain (same content)
python3 -I -c "import json,sys; open(sys.argv[2],'w').write(json.dumps(json.load(open(sys.argv[1])))+'\n')" $HEAD $O/head.json
python3 -I $HERE/to_channel.py $S $O/head.json $O/ch.json '*_su_l0__*' $CH > $O/to_channel.json
python3 -I -c "import json,sys; open(sys.argv[2],'w').write(json.dumps(json.load(open(sys.argv[1])))+'\n')" $O/ch.json $O/cand1.json
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
