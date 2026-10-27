#!/bin/bash
# HEAD-CORE-LAT-R8 plan sweep with the R8 hull rule (head_tree_plan --hull), uf_phys3 v1 GRT. PLAN MODEL, UNCHECKED.
W=/srv/opentallas-scratch2/claude/wt/head-core-lat-r8-1026
R5=/srv/opentallas-scratch2/claude/head-core-lat-r5-1026
R6=/srv/opentallas-scratch2/claude/head-core-lat-r6-1026
O=/srv/opentallas-scratch2/claude/head-core-lat-r8-1026/p; mkdir -p $O
geo=${GEO:-$R5/geo/elemB_r6.geo}; ent=${ENT:-142.56,142.56}
run() { n=$1; shift
  python3 -I $W/tools/s81_head/head_tree_plan.py $geo $O/$n --entry $ent --seg 1000 "$@" > $O/$n.plan.log 2>&1 || { echo "$n PLANFAIL $(tail -1 $O/$n.plan.log)"; return; }
  echo "$n $(grep ^HULL $O/$n.plan.log)"
  python3 -I $R6/p3_predict.py $R6/mr3 $O/$n.tcl $O/$n.seg.json $O/$n.geo $R5/lib $O/$n.p3.json 2>&1 | tail -1
}
export -f run; export W R5 R6 O geo ent
cat $1 | xargs -P 12 -I{} bash -c "run {}"
