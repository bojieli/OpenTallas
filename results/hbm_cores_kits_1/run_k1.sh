#!/bin/bash
# HBM-CORES-KITS-1: kit wave of the 22 C24 plan-view cores (DIE-HBM-10 18:26 list), main generator via mk_c20.py, shared kit_preflight.
set -u
W=/srv/opentallas-scratch2/claude/wt/hbm-cores-kits-1; P=/srv/opentallas-scratch2/claude/die-hbm-10/c24
D=/srv/opentallas-scratch2/claude/hbm-cores-kits-1/k1; mkdir -p $D; cd $D
echo "$(date) start plan $(cut -c1-12 $P/die_plan.sha256) src $(git -C $W rev-parse --short=10 HEAD)"
( cd $W/physical/die_plan/hbm_arch_cores && python3 views_b2r2.py --plan $P/die_plan.json --out $D/views.json ) > $D/views.log 2>&1; echo "views rc=$?"
cat > $D/mods.txt <<M
hfd_hgi_vm_calendar_f20
ot_hbm_host_cp_rxs
ot_hbm_sm_vm_wr_q_t_lanes4
ot_hbm_su_static_cxport_ij_q
ot_hbm_su_static_qcore_r13
ot_hgi_sm_xload_cl2_ctlx
hfd_hgi_vms_glue_nw_t
hnx_rp3lp3h_n
hnx_rp3lp3h_s
ot_hbm_idx_selector_static_sel
ot_hbm_idx_topk_link_static
ot_hbm_su_programme_pslice_c5
ot_hbm_svc_wb_kport_q
ot_hgi_coll_gq_issue
ot_hgi_dma_back_static_vp4_banks_cp
ot_hgi_qw_dec
ot_hgi_sfu_programme_store_r10
ot_pdie_serdes
ot_hgi_sfu_core_split3__ctl
ot_hgi_sfu_core_split3__opstore_a
ot_hgi_sfu_core_split3__opstore_b
M
split -n r/4 -d $D/mods.txt $D/batch_
for b in batch_00 batch_01 batch_02 batch_03; do
  MKTAG=_$b python3 $W/results/die_hbm_kits_1027/mk_c20.py $P $D/views.json $D/slices_$b $D/kits $W $(paste -sd, $b) --tag _k1c24 > $D/mk_$b.log 2>&1 &
done
wait; echo "$(date) gen done"
mkdir -p $D/preflight
for k in $D/kits/*/; do k=${k%/}; n=$(basename $k); [ -f $k/freeze.json ] || continue
  ( cd $W/tools/die_plan && timeout 1200 python3 kit_preflight.py --contract --plan-dir $P --out $D/preflight/$n.json $k > $D/preflight/$n.txt 2>&1 ) &
done; wait
echo "$(date) preflight done"; touch $D/RUN_DONE
