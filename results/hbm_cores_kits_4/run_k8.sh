#!/bin/bash
# HBM-CORES-KITS-4 k8: qcore_r13 regenerated with the n32 err[1] fix (branch claude/hbm-cores-kits-4-1028), same v6 macro placement as _k6
set -u
W=/srv/opentallas-scratch2/claude/wt/hbm-cores-kits-3; P=/srv/opentallas-scratch2/claude/die-hbm-10/c24; D=/srv/opentallas-scratch2/claude/hbm-cores-kits-4/k8; S=/srv/opentallas-scratch2/claude/hbm-cores-kits-1
mkdir -p $D/preflight
echo "$(date) start src $(git -C $W rev-parse --short=10 HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l)"
M=$W/results/hbm_cores_kits_2/mp
python3 $W/results/die_hbm_kits_1027/mk_c20.py $P $S/k3/views.json $D/slices_b $D/kits $W ot_hbm_su_static_qcore_r13 --tag _k8 --gen-args "--macro-placement $M/ot_hbm_su_static_qcore_r13_v6.json --macro-inst-fmt {k}" > $D/mk_b.log 2>&1
echo "$(date) gen done"
for k in $D/kits/*/; do k=${k%/}; n=$(basename $k); [ -f $k/freeze.json ] || continue
  ( cd $W/tools/die_plan && timeout 1800 python3 kit_preflight.py --contract --plan-dir $P --out $D/preflight/$n.json $k > $D/preflight/$n.txt 2>&1; echo "preflight rc=$?" >> $D/preflight/$n.txt )
done
echo "$(date) done"; touch $D/RUN_DONE
