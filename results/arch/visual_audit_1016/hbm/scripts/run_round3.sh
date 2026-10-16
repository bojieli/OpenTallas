#!/bin/bash
F=/home/ubuntu/wt/visaudit-hbm-1016/results/arch/visual_audit_1016/hbm/scripts/fetch_render.sh
export CLKS=clk,clk_macro,clk_hbm,clk_stream,ot_entry_0,clk_core,clk_sram
S=/srv/opentallas-scratch/claude/closure-loop; S2=/srv/opentallas-scratch2/claude/closure-loop; G=/srv/opentallas-scratch/claude/ref_gate
while read n h r; do
  ( bash $F $n $h $r > /tmp/claude-1000/visaudit/tiles/$n.fr.log 2>&1; echo "DONE $n $(tail -1 /tmp/claude-1000/visaudit/tiles/$n.fr.log)" ) &
done <<L
vmq0_nat2 ot-epyc4 $S2/vm_native_q0_ref-nat2-f084d0a8b
vmq1_nat2 ot-epyc4 $S2/vm_native_q1_ref-nat2-f084d0a8b
vmq2_nat2 ot-agidock128 $S/vm_native_q2_ref-nat2-ee83da123
smh_rp4c ot-epyc4 $G/smh_tile_rp4c-20261016-061544
smh_rp3 ot-epyc4 $S2/smh_tile_rp3-rp3-76112f61f
sfucore_split ot-epyc4 $G/hbm_sfucore_split-20261016-073718
f20_cal ot-agidock128 $S/hv16_vm_cal_f20-f20-df84589aa
f20_cal_ww ot-agidock128 $S/hv16_vm_cal_f20_ww-ww0900-ad9c630eb
f20_cal_gate ot-epyc4 $G/hv16_vm_cal_f20-20261016-072957
lkep_ep1 ot-pve1 $S/hep_static_ref_1015-ep1-f24bad869
coll_vmw_v6 ot-agidock128 $S/hcoll_vmwrite_static_v6_roots_fsw-fsw0600-d6d487656
xcal216 ot-agidock128 $S/hbm_xcal216_r1-r1-a380caec1
pcctrl_h6 ot-epyc4 $S2/hdie_pc_ctrl_cfg-cfg-h6-nooverflight-west-6a9d24cd2
vmdel_lane ot-agidock128 $S/hv15_vmdel_lane-hv15-20b84db92
rly624_ew ot-agidock128 $S/hbfd_rly_624_ew-nl2-22a84f859
ckgen ot-agidock128 $S/hbm_ckgen_cl-cl1-c3fc50d5c
sfu_store_pve ot-pve1 $G/hbm_sfu_programme_store_1016-20261016-092026
vmq0_faces ot-agidock128 $G/vm_native_q0_faces-20261016-093214
L
wait
