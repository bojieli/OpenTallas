#!/bin/bash
# HBM-CORES-KITS-14 k2: macro kits with R-SRAM-ENTRY placements (results/hbm_cores_kits_3/mp_rule_c.py on the k1 kits + yosys inst lists) + mk_c20 --avoid-macros
set -u
W=/srv/opentallas-scratch2/claude/wt/hbm-cores-kits-14; R=/srv/opentallas-scratch2/claude/hbm-cores-kits-14; P=$R/c25c_d16; D=$R/k2; MP=$R/mp
mkdir -p $D/preflight; cd $D
echo "$(date) start plan $(sha256sum $P/die_plan.json | cut -c1-12) src $(git -C $W rev-parse --short=10 HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l)"
i=0
for m in hnx_rp3lp3h_n hnx_rp3lp3h_s ot_hbm_host_cp_rxs ot_hbm_su_static_pgslice_lg__lanes8_11 hfd_ep_static; do i=$((i+1))
  python3 $W/results/die_hbm_kits_1027/mk_c20.py $P $R/k1/views.json $D/slices_$i $D/kits $W $m --tag _k14m --avoid-macros $MP/$m.json --gen-args "--macro-placement $MP/$m.json --macro-inst-fmt {k}" > $D/mk_$m.log 2>&1 &
done; wait; echo "$(date) gen done"
for k in $D/kits/*/; do k=${k%/}; n=$(basename $k); [ -f $k/freeze.json ] || continue
  ( cd $W/tools/die_plan && timeout 1800 python3 kit_preflight.py --contract --plan-dir $P --out $D/preflight/$n.json $k > $D/preflight/$n.txt 2>&1; echo "preflight rc=$?" >> $D/preflight/$n.txt ) &
done; wait
echo "$(date) preflight done"; touch $D/RUN_DONE
