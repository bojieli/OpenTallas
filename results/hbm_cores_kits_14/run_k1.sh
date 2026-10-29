#!/bin/bash
# HBM-CORES-KITS-14 k1: K5 SU + K8 HNX/PHY kits on plan c25c_d16 (main generator mk_c20, shared kit_preflight --contract)
set -u
W=/srv/opentallas-scratch2/claude/wt/hbm-cores-kits-14; R=/srv/opentallas-scratch2/claude/hbm-cores-kits-14; P=$R/c25c_d16; D=$R/k1
M3=$W/results/hbm_cores_kits_3/mp; M4=$W/results/hbm_cores_kits_4/mp
mkdir -p $D/preflight; cd $D
echo "$(date) start plan $(sha256sum $P/die_plan.json | cut -c1-12) src $(git -C $W rev-parse --short=10 HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l)"
[ -f $D/views.json ] || ( cd $W/physical/die_plan/hbm_arch_cores && python3 views_b2r2.py --plan $P/die_plan.json --out $D/views.json ) > $D/views.log 2>&1
i=0
for m in ot_hbm_su_static_pgslice_lg__pretree ot_hbm_su_static_pgslice_lg__lane_exp0 ot_hbm_su_static_pgslice_lg__lanes8_11 ot_hbm_su_programme_pslice_c5 ot_hbm_su_static_sfustore_hw ot_hbm_su_static_cxport_ij_q hnx_rp3lp3h_n hnx_rp3lp3h_s ot_hbm_host_cp_rxs hfd_ep_static; do
  i=$((i+1)); python3 $W/results/die_hbm_kits_1027/mk_c20.py $P $D/views.json $D/slices_$i $D/kits $W $m --tag _k14 > $D/mk_$m.log 2>&1 &
done
python3 $W/results/die_hbm_kits_1027/mk_c20.py $P $D/views.json $D/slices_q $D/kits $W ot_hbm_su_static_qcore_r13 --tag _k14 --avoid-macros $M4/ot_hbm_su_static_qcore_r13_v6.json --gen-args "--macro-placement $M4/ot_hbm_su_static_qcore_r13_v6.json --macro-inst-fmt {k}" > $D/mk_ot_hbm_su_static_qcore_r13.log 2>&1 &
python3 $W/results/die_hbm_kits_1027/mk_c20.py $P $D/views.json $D/slices_s $D/kits $W ot_pdie_serdes --tag _k14 --avoid-macros $M3/ot_pdie_serdes.json --gen-args "--macro-placement $M3/ot_pdie_serdes.json --macro-inst-fmt {k}" > $D/mk_ot_pdie_serdes.log 2>&1 &
wait; echo "$(date) gen done"
for k in $D/kits/*/; do k=${k%/}; n=$(basename $k); [ -f $k/freeze.json ] || continue
  ( cd $W/tools/die_plan && timeout 1800 python3 kit_preflight.py --contract --plan-dir $P --out $D/preflight/$n.json $k > $D/preflight/$n.txt 2>&1; echo "preflight rc=$?" >> $D/preflight/$n.txt ) &
done; wait
echo "$(date) preflight done"; touch $D/RUN_DONE
