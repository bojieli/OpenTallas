#!/bin/bash
# QC-PLAN-F4A: F4A vmr/rp1 core trees with the router-proof L1 clear route (--clear L1); ctl = same tool without --clear
W=/srv/opentallas-scratch2/claude/wt/qc-plan-f4a-1026
cd $W/results/qc_plan_f4a
LIB=/srv/opentallas-scratch2/claude/master-plan-r4-1026/su_refloor
UF=$W/results/master_plan_r5/su_unequal/su_tree_uf.py
SR=$W/physical/asap7_memory_macros_v2_col
for n in vmr rp1; do
  prlimit --as=16000000000 python3 -u f4_g4c.py ${n}_f4a_g4c $W/results/qc_su_f4/r1/${n}_f4a.geo 6 $LIB $UF $SR ${n}_f4a_g4c --l1 wp --l2 wp --l3 wp --clear L1 --isl-out-pinwin > ${n}_f4a_g4c.log 2>&1 &
  [ -n "$CTL" ] && prlimit --as=16000000000 python3 -u f4_g4c.py ${n}_ctl $W/results/qc_su_f4/r1/${n}_f4a.geo 6 $LIB $UF $SR ctl/${n}_ctl --l1 wp --l2 wp --l3 wp > ctl_${n}.log 2>&1 &
done
wait
