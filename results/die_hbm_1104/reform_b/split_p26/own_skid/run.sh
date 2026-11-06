#!/bin/bash
# HBM-REFORM-B6: svgr_own response cut. Owner table lookup commits into a 2-entry skid per PC; the arbiter reads only the skid.
B=/srv/opentallas-scratch3/claude/hbm-reform-b5/bench; cd $B; export B VL_JOBS=8
OUT=/srv/opentallas-scratch3/claude/hbm-reform-b6/own; S=$OUT/own1.sed; ST=/srv/opentallas-scratch3/claude/hbm-reform-b6/stall/s1.sed
echo "/^module ot_svgr_own #(/s/parameter integer MUT=0)(/parameter integer MUT=5/;/^module ot_svgr_own #(/s/MUT=5/MUT=5)(/" > $OUT/m5.sed
run(){ n=$1; shift; bash mkbench.sh $n "$@" > out/$n.mk 2>&1; bash one.sh $n L00:0 smoke > out/$n.run 2>&1
 echo "$n $(grep -c 'sk_m\[sk_wp\]' tmp_$n/split.sv) $(grep -m1 -E 'SMB_UNIT|FAULT|Error' out/$n.smoke.log | cut -c1-220) | $(tail -1 out/$n.mk | cut -c1-40)" >> $OUT/res.txt; rm -rf work_$n/obj_*; }
run oc0 $S & run oc1 $S $ST & run oc5 $S $ST $OUT/m5.sed & run oc2 $S $ST $B/m_ow1.sed & run oc4 $S $ST $B/m_ow4.sed & wait
echo ALLDONE >> $OUT/res.txt
