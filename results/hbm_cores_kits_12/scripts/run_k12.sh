#!/bin/bash
# HBM-CORES-KITS-12: kits of the c25c_d15 NEEDS-KIT/GEOM-REQ/KIT-PLACED cores, main generator via mk_c20.py, shared kit_preflight --contract.
set -u
W=/srv/opentallas-scratch2/claude/wt/hbm-cores-kits-12; P=/srv/opentallas-scratch2/claude/hbm-cores-kits-12/c25c_d15
D=/srv/opentallas-scratch2/claude/hbm-cores-kits-12/k3; mkdir -p $D; cd $D
cp ../mods.txt $D/mods.txt
echo "$(date) start plan $(sha256sum $P/die_plan.json | cut -c1-12) src $(git -C $W rev-parse --short=10 HEAD)"
( cd $W/physical/die_plan/hbm_arch_cores && python3 views_b2r2.py --plan $P/die_plan.json --out $D/views.json ) > $D/views.log 2>&1; echo "views rc=$?"
split -n r/16 -d $D/mods.txt $D/batch_
for b in $D/batch_*; do b=$(basename $b)
  python3 $W/results/die_hbm_kits_1027/mk_c20.py $P $D/views.json $D/slices_$b $D/kits $W $(paste -sd, $b) --tag _k12 > $D/mk_$b.log 2>&1 &
done
wait; echo "$(date) gen done"
mkdir -p $D/preflight
for k in $D/kits/*/; do k=${k%/}; n=$(basename $k); [ -f $k/freeze.json ] || continue
  ( cd $W/tools/die_plan && timeout 1800 python3 kit_preflight.py --contract --plan-dir $P --out $D/preflight/$n.json $k > $D/preflight/$n.txt 2>&1 ) &
done; wait
echo "$(date) preflight done"; touch $D/RUN_DONE
