#!/bin/bash
# HEAD-CORE-LAT-R6 elemB R6 geometry plan sweep, uf_phys3 v1 (GRT basis). PLAN MODEL, UNCHECKED.
cd /srv/opentallas-scratch2/claude/head-core-lat-r5-1026
R6=/srv/opentallas-scratch2/claude/head-core-lat-r6-1026
run() {  # name fanouts leafcell cell
  n=$1; f=$2; lc=$3; c=$4
  python3 -I head_tree_plan.py geo/elemB_r6.geo $R6/p/$n --entry 142.56,142.56 --fanouts $f --seg 1000 --balance 1 \
     --leafcell $lc --cell $c > $R6/p/$n.plan.log 2>&1 || { echo "$n PLANFAIL"; return; }
  python3 -I $R6/p3_predict.py $R6/mr3 $R6/p/$n.tcl $R6/p/$n.seg.json $R6/p/$n.geo lib $R6/pred/$n.p3.json 2>&1 | tail -1
}
X24=BUFx24_ASAP7_75t_R; X16=BUFx16f_ASAP7_75t_R; X12=BUFx12f_ASAP7_75t_R; X8=BUFx8_ASAP7_75t_R
run br6_44442_x16 4,4,4,4,2 $X16 $X24 &
run br6_44442_x12 4,4,4,4,2 $X12 $X24 &
run br6_444222 4,4,4,2,2,2 $X24 $X24 &
run br6_444222_x16 4,4,4,2,2,2 $X16 $X24 &
run br6_2244442 2,2,4,4,4,2 $X24 $X24 &
run br6_44442_c16 4,4,4,4,2 $X24 $X16 &
run br6_44442_c16x16 4,4,4,4,2 $X16 $X16 &
run br6_4444_x24 4,4,4,4 $X24 $X24 &
wait
