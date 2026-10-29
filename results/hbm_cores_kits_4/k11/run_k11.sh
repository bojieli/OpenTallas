#!/bin/bash
# HBM-CORES-KITS-4 k11: macro kits whose 12.8b leaf islands sat on SRAMs, regenerated with mk_c20 --avoid-macros
set -u
W=/srv/opentallas-scratch2/claude/wt/hbm-cores-kits-3; D=/srv/opentallas-scratch2/claude/hbm-cores-kits-4/k11
P25=/srv/opentallas-scratch2/claude/die-hbm-10/c25a; P24=/srv/opentallas-scratch2/claude/die-hbm-10/c24
V25=/srv/opentallas-scratch2/claude/hbm-cores-kits-4/k9/views.json; S=/srv/opentallas-scratch2/claude/hbm-cores-kits-1
M3=$W/results/hbm_cores_kits_3/mp; M4=$W/results/hbm_cores_kits_4/mp
mkdir -p $D/preflight; cd $D
echo "$(date) start src $(git -C $W rev-parse --short=10 HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l)"
i=0
for m in ot_hbm_idx_topk_link_static ot_hbm_svc_sm_group_rel_id ot_hbm_idx_selector_static_sel ot_hbm_svc_wb_kport_q hfd_hgi_vm_calendar_f20; do
  i=$((i+1))
  python3 $W/results/die_hbm_kits_1027/mk_c20.py $P25 $V25 $D/slices_$i $D/kits $W $m --tag _k11 --avoid-macros $M3/$m.json --gen-args "--macro-placement $M3/$m.json --macro-inst-fmt {k}" > $D/mk_$m.log 2>&1 &
done
python3 $W/results/die_hbm_kits_1027/mk_c20.py $P24 $S/k3/views.json $D/slices_q $D/kits $W ot_hbm_su_static_qcore_r13 --tag _k11 --avoid-macros $M4/ot_hbm_su_static_qcore_r13_v6.json --gen-args "--macro-placement $M4/ot_hbm_su_static_qcore_r13_v6.json --macro-inst-fmt {k}" > $D/mk_qcore.log 2>&1 &
python3 $W/results/die_hbm_kits_1027/mk_c20.py $P24 $S/k1/views.json $D/slices_s $D/kits $W ot_pdie_serdes --tag _k11 --avoid-macros $M3/ot_pdie_serdes.json --gen-args "--macro-placement $M3/ot_pdie_serdes.json --macro-inst-fmt {k}" > $D/mk_serdes.log 2>&1 &
wait; echo "$(date) gen done"
for k in $D/kits/*/; do k=${k%/}; n=$(basename $k); [ -f $k/freeze.json ] || continue
  P=$P25; case $n in *qcore_r13*|*serdes*) P=$P24;; esac
  ( cd $W/tools/die_plan && timeout 1800 python3 kit_preflight.py --contract --plan-dir $P --out $D/preflight/$n.json $k > $D/preflight/$n.txt 2>&1; echo "preflight rc=$?" >> $D/preflight/$n.txt ) &
done
wait; python3 /srv/opentallas-scratch2/claude/hbm-cores-kits-4/islchk.py $W/tools/die_plan $D/kits/*-_k11 > $D/islchk.txt 2>&1
echo "$(date) done"; touch $D/RUN_DONE
