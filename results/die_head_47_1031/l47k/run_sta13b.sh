#!/bin/bash
# DIE-HEAD-47 HEAD die STA, 12.25 form (KV recipe flags; OWNER 12.24b/c: nominal clock - no spice x1.05, no clock OCV table,
# no droop - +10 ps hold margin restored; landed hops = count-aligned rings, bind hk5_leaf2 = plan K for 427/427 ports)
# usage: run_sta.sh PROOF_DIR OUT KEY
set -u; S=/srv/opentallas-scratch2/claude/die-head-47; M=$S/mt13; P=$1; O=$2; K=${3:-part}
V=$S/mt/results/die_head_1027/views
rm -rf $O; mkdir -p $O
python3 $M/tools/die_plan/die_sta_related.py $P --plan $S/head_source_l47/source_plan.json --out $O --corner TT --corner FF \
  --cppr-lca --clock-cell inv --margin-policy nominal --hold-buffers HB4 --core-latency-ff 342 \
  --core-view ot_s81hd_elemA_cv=$V/ot_s81hd_elemA_cv --core-view ot_s81hd_elemB_cv=$V/ot_s81hd_elemB_cv \
  --count-align ${BIND:-$S/sta/bind_hk5.json} --count-align-key $K ${RING:+--ca-ring $RING} > $O.log 2>&1; echo rc $?
