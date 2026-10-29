#!/bin/bash
# HBM-CORES-KITS-12 wave k4: K1 HUB-VMS + K4 IDX kits on plan c25c_d16 (6ba9f877d23f), main generator via mk_c20.py,
# plan core_macros.json KNOWN rects -> mp JSON (cm2mp.py) for macro cores, shared kit_preflight --contract.
set -u
W=/srv/opentallas-scratch2/claude/wt/hbm-cores-kits-12; B=/srv/opentallas-scratch2/claude/hbm-cores-kits-12; P=$B/c25c_d16
D=$B/k4; mkdir -p $D/preflight; cd $D
echo "$(date) start plan $(sha256sum $P/die_plan.json | cut -c1-12) src $(git -C $W rev-parse --short=10 HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l)"
MK="python3 $W/results/die_hbm_kits_1027/mk_c20.py $P $D/views.json"
for m in ot_hbm_idx_qctl_static ot_hbm_idx_query_static ot_hbm_idx_rootctl_static_am ot_hbm_svc_vmdel_lane_n ot_hbm_svc_sm_xcal_rel_t; do
  $MK $D/sl_$m $D/kits $W $m --tag _k12d16 --avoid-macros $B/mp/$m.json --gen-args "--macro-placement $B/mp/$m.json --macro-inst-fmt {k}" > $D/mk_$m.log 2>&1 &
done
$MK $D/sl_glue $D/kits $W hfd_hgi_vms_glue_nw_t --tag _k12d16 > $D/mk_glue.log 2>&1 &
$MK $D/sl_hcolA $D/kits $W ot_hbm_idx_score_hcol_h0,ot_hbm_idx_score_hcol_h1 --tag _k12d16A > $D/mk_hcolA.log 2>&1 &
$MK $D/sl_hcolB $D/kits $W ot_hbm_idx_score_hcol_h0,ot_hbm_idx_score_hcol_h1 --tag _k12d16B --gen-args "--face-shell off" > $D/mk_hcolB.log 2>&1 &
wait; echo "$(date) gen done"
for k in $D/kits/*/; do k=${k%/}; n=$(basename $k); [ -f $k/freeze.json ] || continue
  ( cd $W/tools/die_plan && timeout 1800 python3 kit_preflight.py --contract --plan-dir $P --out $D/preflight/$n.json $k > $D/preflight/$n.txt 2>&1 ) &
done; wait
echo "$(date) preflight done"; touch $D/RUN_DONE
