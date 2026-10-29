#!/bin/bash
set -u
W=/srv/opentallas-scratch2/claude/wt/hbm-cores-kits-12; B=/srv/opentallas-scratch2/claude/hbm-cores-kits-12; P=$B/c25c_d16; D=$B/k5; mkdir -p $D/preflight; cd $D; cp $B/k4/views.json .
echo "$(date) start"
MK="python3 $W/results/die_hbm_kits_1027/mk_c20.py $P $D/views.json"
$MK $D/sl_r $D/kits $W ot_hbm_idx_rootctl_static_am --tag _k12d16 --avoid-macros $B/mp/ot_hbm_idx_rootctl_static_am.json --gen-args "--macro-placement $B/mp/ot_hbm_idx_rootctl_static_am.json --macro-inst-fmt {k}" > mk_r.log 2>&1 &
$MK $D/sl_x $D/kits $W ot_hbm_svc_sm_xcal_rel_t --tag _k12d16v --avoid-macros $B/mp/ot_hbm_svc_sm_xcal_rel_t_v.json --gen-args "--macro-placement $B/mp/ot_hbm_svc_sm_xcal_rel_t_v.json --macro-inst-fmt {k}" > mk_x.log 2>&1 &
wait
for k in $D/kits/*/; do k=${k%/}; n=$(basename $k); [ -f $k/freeze.json ] || continue
  ( cd $W/tools/die_plan && timeout 1800 python3 kit_preflight.py --contract --plan-dir $P --out $D/preflight/$n.json $k > $D/preflight/$n.txt 2>&1 ) &
done; wait; echo "$(date) done"; touch $D/RUN_DONE
