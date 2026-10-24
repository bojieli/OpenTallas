# Open hard elements per the 10-21 release tree (element table 2026-10-21 19:35), extracted 2026-10-24
Source: ~/coord/RELEASE_TREE_1021.html (text: ~/coord/old_tree.txt). Format: group N/M closed, worst open element, status, last numbers.

## S81 DeepSeek ROM
- gunit 9/10 closed in flight dsdv_gunit master S81-DIE6 parent open, leaves under way

## Qwen compute
- Slices, clusters and stations 2/5 closed kit prepared, no route job qfd_c_b16_dv master Q-DIE11b kit prepared, no route job
- Host, sequencer, services and control 3/5 closed open, no live job qfd_native59_dv_service master qfd_native59_dv_service-n1-e4ecec634 Q-DIE11b needs redesign (no live job)

## Qwen KV
- Vector memory, HBM controller, banks 4/9 closed open, no live job qkd_kvs_grp master qkd_kvs_grp_k1-k1-5561116d2 KV-PLAN4 needs redesign (no live job)
- Attention 17/20 closed open, no live job qkd_pv_fin_s master qkd_pv_fin_s-g1-7834bbc26 KV-PLAN4 needs redesign (no live job)
- Die links: PHY, D2D, SerDes, UCIe 1/2 closed closed, not die-bindable qkd_d2d_static master qkd_d2d_static_r7v-r7v-1b609a25c TT +13.6 / FF +7.7 KV-PLAN4 native TT pin-flop spread 84.0 > 80; spread 84.0 > 80
- Host, sequencer, services and control 8/9 closed in flight qkd_host_root_admission master KV-PLAN4 parent open, leaves under way

## HBM
- Vector memory, HBM controller, banks 11/24 closed open, no live job ot_hbm_hc_bankq0_static master hbm_hcq_bank_b0_1017-ring1-47247cc08 H-D4G cancelled only
- Collectives and argmax 12/18 closed open, no live job ot_hgi_coll_gq_issue master hcoll_gq_issue_k9q_1020-k9q-dccd7469a TT -98.2 / FF -27.7 H-D4G needs redesign (no live job)
- Index (IDX) 6/10 closed open, no live job ot_hbm_idx_selector_static master hidx_sel_g4p-g4p-90b8aed47 H-D4G needs redesign (no live job)
- Stream unit (SU) 14/18 closed kit prepared, no route job ot_hbm_su_static_cxport_ij master H-D4G kit prepared, no route job
- Attention 0/2 closed open, no live job ot_hbm_sm_pv_merge leaf (RTL hierarchy) of ot_hbm_accel_smh_attn smh_pvm_ref_r4-r3-f63e66b4c TT -125.4 / FF -17.6 H-D4G needs redesign (no live job)
- Die links: PHY, D2D, SerDes, UCIe 0/2 closed in flight ot_pdie_serdes master S81-DIE6 parent open, leaves under way
- SFU 5/7 closed open, no live job ot_hgi_sfu_core_split3 master hbm_sfucore_k9y-y1-d285e0902 H-D4G needs redesign (no live job)
- Matrix engine (SM) 7/8 closed kit prepared, no route job ot_hbm_svc_sm_group_id master H-D4G kit prepared, no route job

Also not die-bindable although 'closed' (pin-flop spread > 80 ps): dsdv_bk_col 105.9, dsdv_sh_lk 85.4, dsfd_coll_lane_w, qkd_d2d_static 84.0.
