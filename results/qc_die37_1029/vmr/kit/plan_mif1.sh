#!/bin/bash
# DIE-QC-37 VMR MIF1: F4D plan recipe (results/qc_su_f4d/run_f4d.sh, claude/qc-su-f4d-1026@d4d7ecb34) on a placed geo,
# then the F4F common-entry trunk (TR0..TR3, cells/sites identical to vmr_f4k_final mscts_spec_f4f.tcl) spliced in.
#   plan_mif1.sh GEO OUTDIR    (GEO.json = macro meta)
set -e
B=/srv/opentallas-scratch2/claude/die-qc-37-vmr; W=$B/f4d_tools; D=$W/results/qc_su_f4d; LIB=$B/invbuf/lib
G=$1; O=$2; mkdir -p $O; cd $O
export OT_PHYS_FIT=$W/results/model_refit3_1026/uf_phys3_v1.json
prlimit --as=16000000000 python3 -u $D/f4_g4d.py vmr_k8 $G 8 $LIB $W/results/qc_su_f4c/su_tree_eq_f4c.py $W/physical/asap7_memory_macros_v2_col vmr_k8 \
   --l1 spw --l2 spw --l3 spw --clear L1 --isl-out-pinwin --no-trunk > vmr_k8.log 2>&1
grep -H "VERDICT" vmr_k8.log
python3 $D/detour.py vmr_k8.json vmr_k8_detour.json > vmr_k8_detour.txt
cd $D/pred
python3 f4d_pred3.py $W $O/vmr_k8.tcl $G $LIB $O/vmr_k8_m56.json m56 --seg-plan $O/vmr_k8.json
python3 f4d_size.py $W $O/vmr_k8.tcl $G $LIB $O/vmr_k8_s56.tcl --layers m56 --passes 4 --window-only --seg-plan $O/vmr_k8.json > $O/vmr_k8_s56.log 2>&1
for L in m56 m45; do python3 f4d_pred3.py $W $O/vmr_k8_s56.tcl $G $LIB $O/vmr_k8_s56_$L.json $L --seg-plan $O/vmr_k8.json; done
tail -1 $O/vmr_k8_s56.log
python3 render_f4d.py $O/vmr_k8_s56.tcl $G $O/vmr_k8.json $O/vmr_k8_s56.png "DIE-QC-37 VMR MIF1 8x8 spw, d1 window-only" || true
