#!/bin/bash
# DIE-HBM-4-KITS 10-28 (GEOM-REVIEW-40 FAILs 68d657fa5a42 ring_ag, f287d70d8655 tkm tile_core idpin strap):
#   plan c20e_k2 = c20e + apply_q2_qid_mid.py (q2 ring_ag qid[1:0] -> W-face middle, order-preserving rotation);
#   tkm tile_core: same plan pins, PLACE_DENSITY via the generator knob --util (0.25 primary, 0.30 alternate) instead
#   of the 0.5 default (fill .194).  Then shared kit_preflight and place-only (run_kit_hbm.sh GOAL=place) via ot-run.
set -u
W=/srv/opentallas-scratch2/claude/wt/die-hbm-kits-2-1027; B=/srv/opentallas-scratch2/claude/die-hbm-1027
C=$B/kits/c20e; D=$B/kits/c20e_k2; K=$D/kits; F=$B/kits/fixes; G=$W/physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py
cp -a $B/c20e $B/c20e_k2 && rm -rf $B/c20e_k2/gates
python3 $W/results/die_hbm_kits_1027/apply_q2_qid_mid.py $B/c20e_k2 --report $B/c20e_k2/q2_qid_mid_delta_report.json
mkdir -p $K $D/place; cd $W/physical/die_plan/hbm_arch_cores
python3 views_b2r2.py --plan $B/c20e_k2/die_plan.json --out $D/views.json
m=ot_hfd_coll_q2_hard_v8g__ring_ag
python3 $G --views $D/views.json --view $m@bbea2db4b304 --out $K --master-slice $C/slices_batch_03 --trial --tag _c20ek2 \
  --wrapper $F/q2_oneclk_wrappers/$m.sv > $K/gen_$m.log 2>&1
m=ot_hgi_coll_tkm_tp192_tile_core__idpin__strap
python3 $G --views $D/views.json --view $m@61e365d09ac2 --out $K --master-slice $C/slices_batch_03 --trial --tag _c20ek2_d25 --util 0.25 > $K/gen_$m.log 2>&1
python3 $G --views $D/views.json --view $m@61e365d09ac2 --out $K --master-slice $C/slices_batch_03 --trial --tag _c20ek2_d30 --util 0.30 > $K/gen_${m}_d30.log 2>&1
bash $W/results/die_hbm_kits_1027/pf_all.sh $B/c20e_k2 $K $D/preflight $W
for k in $K/*/; do k=${k%/}; n=$(basename $k)
  ~/.local/bin/ot-run --mem 32 --threads 16 --dir $k -- bash $k/run_kit_hbm.sh $k place 32 16 > $D/place/$n.otrun.log 2>&1 &
done; wait
