#!/bin/bash
# QC-SU-PROG-L2 sweep: 3-level H-tree (ht_l2.py) on the GEOM-6-approved H5 L1, D2 x SEG, refit4 gate; then renders
W=/srv/opentallas-scratch2/claude/wt/qc-su-prog-l2-1026; C=$W/results/qc_su_prog_l1_1026; LIB=/srv/opentallas-scratch2/claude/qc-su-prog-l1-1026/in/lib
export OT_PHYS_FIT=$W/results/model_refit2_1026/refit4/uf_phys_refit4.json OT_SIZE_WORKERS=6
cd $W/results/qc_su_prog_l2_1026/sweep
for d in 50 55 60; do for s in 60 95; do
  (python3 -u $C/ht_l2.py $C/sweep_h/htl1_H5.ht.json h3_d${d}_s${s} $LIB --d2 $d --seg $s > h3_d${d}_s${s}.log 2>&1; python3 $C/render_ht2.py h3_d${d}_s${s}.ht2.json h3_d${d}_s${s}.png) &
done; done; wait; echo SWEEP_DONE
