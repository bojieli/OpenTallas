#!/bin/bash
# HBM-CORES-KITS-4 k9: the multi-clock cores from C25a (20d73dea, clock pins M5) with R-SRAM-ENTRY placements (mp_rule_c.py)
set -u
W=/srv/opentallas-scratch2/claude/wt/hbm-cores-kits-3; P=/srv/opentallas-scratch2/claude/die-hbm-10/c25a; D=/srv/opentallas-scratch2/claude/hbm-cores-kits-4/k9
M=$W/results/hbm_cores_kits_3/mp
mkdir -p $D/preflight; cd $D
echo "$(date) start plan $(sha256sum $P/die_plan.json | cut -c1-8) src $(git -C $W rev-parse --short=10 HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l)"
( cd $W/physical/die_plan/hbm_arch_cores && python3 views_b2r2.py --plan $P/die_plan.json --out $D/views.json ) > $D/views.log 2>&1; echo "views rc=$?"
i=0
for m in ot_hbm_sm_vm_wr_q_t_lanes4 ot_hgi_sm_xload_cl2_ctlx; do
  i=$((i+1))
  python3 $W/results/die_hbm_kits_1027/mk_c20.py $P $D/views.json $D/slices_$i $D/kits $W $m --tag _k10 --gen-args "--macro-placement $M/$m.json --macro-inst-fmt {k}" > $D/mk_$m.log 2>&1 &
done
wait; echo "$(date) gen done"
for k in $D/kits/*/; do k=${k%/}; n=$(basename $k); [ -f $k/freeze.json ] || continue
  ( cd $W/tools/die_plan && timeout 1800 python3 kit_preflight.py --contract --plan-dir $P --out $D/preflight/$n.json $k > $D/preflight/$n.txt 2>&1; echo "preflight rc=$?" >> $D/preflight/$n.txt ) &
done
wait; echo "$(date) done"; touch $D/RUN_DONE
