#!/bin/bash
# HBM-CORES-KITS-2 k6: the 3 kits regenerated from the committed branch (clean worktree) for the queue rows
set -u
W=/srv/opentallas-scratch2/claude/wt/hbm-cores-kits-1; P=/srv/opentallas-scratch2/claude/die-hbm-10/c24; D=/srv/opentallas-scratch2/claude/hbm-cores-kits-2/k6; S=/srv/opentallas-scratch2/claude/hbm-cores-kits-1
echo "$(date) start src $(git -C $W rev-parse --short=10 HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l)"
M=$W/results/hbm_cores_kits_2/mp
python3 $W/results/die_hbm_kits_1027/mk_c20.py $P $S/k2/views.json $D/slices_a $D/kits $W ot_hbm_svc_pc_ctrl_leaf_cfg_h9b --tag _k6 --gen-args "--macro-placement $M/ot_hbm_svc_pc_ctrl_leaf_cfg_h9b.json --macro-inst-fmt {k}" > $D/mk_a.log 2>&1 &
python3 $W/results/die_hbm_kits_1027/mk_c20.py $P $S/k3/views.json $D/slices_b $D/kits $W ot_hbm_su_static_qcore_r13 --tag _k6 --gen-args "--macro-placement $M/ot_hbm_su_static_qcore_r13_v6.json --macro-inst-fmt {k}" > $D/mk_b.log 2>&1 &
python3 $W/results/die_hbm_kits_1027/mk_c20.py $P $S/k1/views.json $D/slices_c $D/kits $W hfd_hgi_vms_glue_nw_t --tag _k6 > $D/mk_c.log 2>&1 &
wait; echo "$(date) gen done"
for k in $D/kits/*/; do k=${k%/}; n=$(basename $k); [ -f $k/freeze.json ] || continue
  ( cd $W/tools/die_plan && timeout 1800 python3 kit_preflight.py --contract --plan-dir $P --out $D/preflight/$n.json $k > $D/preflight/$n.txt 2>&1 ) &
done; wait; echo "$(date) preflight done"; touch $D/RUN_DONE
