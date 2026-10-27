#!/bin/bash
# QC-SU-F4C: equal-island re-plan (k=4 -> 4x16, k=8 -> 8x8) of vmr/rp1 on the F4A placed sink geometry, f4_g4c G1-G5 + router-proof L1
W=$(cd "$(dirname "$0")/../.." && pwd)
LIB=/srv/opentallas-scratch2/claude/master-plan-r4-1026/su_refloor
SR=$W/physical/asap7_memory_macros_v2_col
for n in vmr rp1; do for k in ${KS:-4 8}; do
  prlimit --as=16000000000 python3 -u $W/results/qc_plan_f4a/f4_g4c.py ${n}_k${k} $D/plan/${n}_placed.geo $k $LIB $D/su_tree_eq_f4c.py $SR ${n}_k${k} --l1 wp --l2 wp --l3 wp --clear L1 --isl-out-pinwin $EXTRA > ${n}_k${k}.log 2>&1 &
done; done; wait
grep -H "VERDICT\| BAND" *.log | cut -c1-300
