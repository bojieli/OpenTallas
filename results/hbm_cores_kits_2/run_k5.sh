#!/bin/bash
# HBM-CORES-KITS-2 k5: vms_glue_nw_t regenerated with the gen _um() outline fix (was DIE_AREA 1635.55 vs plan 1635.552)
set -u
W=/srv/opentallas-scratch2/claude/wt/hbm-cores-kits-1; P=/srv/opentallas-scratch2/claude/die-hbm-10/c24; D=/srv/opentallas-scratch2/claude/hbm-cores-kits-2/k5; S=/srv/opentallas-scratch2/claude/hbm-cores-kits-1
echo "$(date) start src $(git -C $W rev-parse --short=10 HEAD) + worktree diff $(git -C $W diff | sha256sum | cut -c1-12)"
python3 $W/results/die_hbm_kits_1027/mk_c20.py $P $S/k1/views.json $D/slices $D/kits $W hfd_hgi_vms_glue_nw_t --tag _k5um > $D/mk.log 2>&1
echo "$(date) gen done"
for k in $D/kits/*/; do k=${k%/}; n=$(basename $k); [ -f $k/freeze.json ] || continue
  ( cd $W/tools/die_plan && timeout 1800 python3 kit_preflight.py --contract --plan-dir $P --out $D/preflight/$n.json $k > $D/preflight/$n.txt 2>&1 )
done; echo "$(date) preflight done"; touch $D/RUN_DONE
