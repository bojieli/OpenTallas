#!/bin/bash
# HBM-CORES-KITS-1: kit wave of the 22 C24 plan-view cores (DIE-HBM-10 18:26 list), main generator via mk_c20.py, shared kit_preflight.
set -u
W=/srv/opentallas-scratch2/claude/wt/hbm-cores-kits-1; P=/srv/opentallas-scratch2/claude/die-hbm-10/c24
D=/srv/opentallas-scratch2/claude/hbm-cores-kits-1/k2; mkdir -p $D; cd $D
echo "$(date) start plan $(cut -c1-12 $P/die_plan.sha256) src $(git -C $W rev-parse --short=10 HEAD)"
( cd $W/physical/die_plan/hbm_arch_cores && python3 views_b2r2.py --plan $P/die_plan.json --out $D/views.json ) > $D/views.log 2>&1; echo "views rc=$?"
cat > $D/mods.txt <<M
ot_hbm_svc_pc_ctrl_leaf_cfg_h9b
hnx_vms_bank_q0_faces__vec6293
hnx_vms_bank_q0_faces__vecd4ae
ot_hbm_svc_sm_group_rel_id
ot_hgi_sm_xload_cl2_bdring
M
split -n r/4 -d $D/mods.txt $D/batch_
for b in batch_00 batch_01 batch_02 batch_03; do
  MKTAG=_$b python3 $W/results/die_hbm_kits_1027/mk_c20.py $P $D/views.json $D/slices_$b $D/kits $W $(paste -sd, $b) --tag _k2c24 > $D/mk_$b.log 2>&1 &
done
wait; echo "$(date) gen done"
mkdir -p $D/preflight
for k in $D/kits/*/; do k=${k%/}; n=$(basename $k); [ -f $k/freeze.json ] || continue
  ( cd $W/tools/die_plan && timeout 1200 python3 kit_preflight.py --contract --plan-dir $P --out $D/preflight/$n.json $k > $D/preflight/$n.txt 2>&1 ) &
done; wait
echo "$(date) preflight done"; touch $D/RUN_DONE
