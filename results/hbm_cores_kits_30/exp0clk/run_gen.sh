#!/bin/bash
# HBM-CORES-KITS-30: lane_exp0_id kit on HBM PoR d44f (exp0 ONE clock pin clk, COORD ruling B), recipe as K28 run_gen.sh.
set -u
W=/srv/opentallas-scratch2/claude/wt/hbm-k30; D=/srv/opentallas-scratch2/claude/hbm-cores-kits-30/exp0clk; P=/srv/opentallas-scratch2/claude/die-hbm-44/plan/d44f
MK=$W/results/die_hbm_kits_1027/mk_c20.py; CM=/srv/opentallas-scratch2/claude/hbm-cores-kits-17/cm2mp.py
m=ot_hbm_su_static_pgslice_lg__lane_exp0_id; RK=ot_hbm_su_static_pgslice_lg__lane_exp0__440.64x457.92
mkdir -p $D/preflight $D/mp $D/kits; cd $D
echo "$(date) start src $(git -C $W rev-parse --short=11 HEAD) d44f $(sha256sum $P/die_plan.json | cut -c1-12)"
python3 $CM $P/core_macros.json $W $m $D/mp/$m.json > $D/mp/$m.log 2>&1; cat $D/mp/$m.log
python3 $MK $P $D/views_d44f.json $D/sl_$m $D/kits $W $m --tag _k30c --ft-pin-dx-um 1.08 --avoid-macros $D/mp/$m.json --gen-args "--macro-placement $D/mp/$m.json --macro-inst-fmt {k} --recipe-key $RK --hold-margin 10" > $D/mk_$m.log 2>&1
echo "mk: $(tail -1 mk_$m.log | cut -c1-600)"
for k in $D/kits/${m}_*-_k30c; do n=$(basename $k); [ -f $k/freeze.json ] || { echo "$n no freeze"; continue; }
  ( cd $W/tools/die_plan && timeout 1800 python3 kit_preflight.py --contract --plan-dir $P --out $D/preflight/$n.json $k > $D/preflight/$n.txt 2>&1; echo "preflight rc=$?" >> $D/preflight/$n.txt )
  tail -4 $D/preflight/$n.txt
done
echo "$(date) preflight done"
