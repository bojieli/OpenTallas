#!/bin/bash
# QC-SU-F4D reproduce: straight-leg (spw) 8x8 equal-leaf re-plan of vmr/rp1 on the F4A MIF0 placed sinks (same island
# structure su_tree_eq_f4c, --clear L1 router-proof, islands out of pin windows, no entry trunk), then 12.8 d1 window-only
# sizing (BUFx8..x24) by uf_phys3 v1 on M5/M6 leg RC with the planned maze leg lengths, re-predict (m56 + m45 risk),
# detour census, render.  PLAN MODEL, UNCHECKED.
set -e
W=$(cd "$(dirname "$0")/../.." && pwd); D=$W/results/qc_su_f4d
LIB=${LIB:-/srv/opentallas-scratch2/claude/master-plan-r4-1026/su_refloor}
export OT_PHYS_FIT=$W/results/model_refit3_1026/uf_phys3_v1.json
for n in vmr rp1; do
  G=$W/results/qc_su_f4c/plan/${n}_placed.geo
  (cd $D/plan && prlimit --as=16000000000 python3 -u $D/f4_g4d.py ${n}_k8 $G 8 $LIB $D/su_tree_eq_f4c.py $W/physical/asap7_memory_macros_v2_col ${n}_k8 \
      --l1 spw --l2 spw --l3 spw --clear L1 --isl-out-pinwin --no-trunk > ${n}_k8.log 2>&1)
  python3 $D/detour.py $D/plan/${n}_k8.json $D/plan/${n}_k8_detour.json > $D/plan/${n}_k8_detour.txt
  cd $D/pred
  python3 f4d_pred3.py $W $D/plan/${n}_k8.tcl $G $LIB ${n}_k8_m56.json m56 --seg-plan $D/plan/${n}_k8.json
  python3 f4d_size.py $W $D/plan/${n}_k8.tcl $G $LIB ${n}_k8_s56.tcl --layers m56 --passes 4 --window-only --seg-plan $D/plan/${n}_k8.json > ${n}_k8_s56.log 2>&1
  for L in m56 m45; do python3 f4d_pred3.py $W ${n}_k8_s56.tcl $G $LIB ${n}_k8_s56_$L.json $L --seg-plan $D/plan/${n}_k8.json; done
  python3 render_f4d.py ${n}_k8_s56.tcl $G $D/plan/${n}_k8.json ${n}_k8_s56.png "QC-SU-F4D $n 8x8 straight legs (spw), d1 window-only sizing, no entry delay"
done
