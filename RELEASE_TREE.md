# OpenTallas release tree (pending only; coordinator update 2026-11-01 18:00 PST)

2026-11-12 01:45 count 272 (flat since 08:05; 58 types + 214 cores). Main 83e9f033ecb0 (3 trains this hour: failfast/free-not-run/wave-balance/HBM d55a+rd1+xtap/kv99; station-bits/edge-float/QC s26/prov-fnf; all-wide float/bandsearch/QC sc+sta forms/autoclean expiry/obs-sync). In flight: S81 col 40, QC re-layout 22, land-ring 52, S81 slice 17, svc_rs 8, HEAD lep0N 5; none at sign-off yet. HBM wave repointing t20io -> t39w (d55a). Explorer on :8760, signed export 22/58 types 112/215 cores.
Plans 11:36: count 152 flat (S81 50/58 + 4/205 types, HEAD 4/4 + 12/25, QC 16/19, KV 26/32, HBM 40/103). Merged I118-I126 since 10:40: QC coll_core fold + ring ff class (tag e-qc), KV PV taps (tag b-kv), HEAD l48ue (tag a-head), wave prune + resume fixes. 9 core gaps from CORE-FORMS-2 all owned. intel2 scratch2 142 after 49 GB move.

<!-- BREAKDOWN BEGIN -->
## FAILURES · unsigned cores and types by class (auto, 2026-11-12 00:37 PST)
- [ ] FAIL.S81.CORES 63/87 signed · open: no kit-wave row 23 (dsdv_gunit_l1f_bf, hdc_v41x_attn_tr_x, s81_su_smc, +6) · running, no result 1 (dsdv_bksel_q)
- [ ] FAIL.S81.TYPES 35/204 signed · kit rows: cancelled (superseded) 93 (col_h10_r1__t1__cl95b37463, +92) · other flow error 45 (bk_sel__t2, +44) · infra (relaunch queued) 28 (col_h10_r1__t1__cld01bb4ae, +27) · running 12 · congestion 12 (col_h9_r0_p2__t1__cl9f71e63d, +11) · stopped (ruling/infra) 3 (col_h10_r0_p1__t1__cl574cc59d, +2) · LEC 2 (dsdv_slice_c1x_C__t6, +1) · port mismatch 2 (dsdv_slice_c3x_C__t1, +1) · timing after route 2 (iqf__t1, +1)
- [ ] FAIL.HEAD.CORES 4/4 signed · open: none
- [ ] FAIL.HEAD.TYPES 19/25 signed · kit rows: cancelled (superseded) 7 (hd_ctl_e, +6) · timing after route 2 (hd_spn, +1) · running 2 · other flow error 1 (hd_host_e)
- [ ] FAIL.QC.CORES 26/26 signed · open: none
- [ ] FAIL.QC.TYPES 2/116 signed · kit rows: running 54 · other flow error 13 (coll_ft__cl78c7b300, +12) · running (>150k advisory) 7 (sle_fw_v2__cl6740750e, +6) · LEC 2 (glue, +1) · cancelled (superseded) 2 (sle_hc2__cl9c4c4509__cl3edce1b8, +1) · timing after route 2 (coll_ftc, +1) · SETUP-AT-GRT 1 (tt_ctlm) · congestion 1 (slw_fe_v1__clfe325744__cl08d14f0d) · stopped (ruling/infra) 1 (slw_fw_v1__clf51c11d8__cl592e3d37) · kit_rtl 1 (cbn_q00__cldbcda913)
- [ ] FAIL.KV.CORES 32/32 signed · open: none
- [ ] FAIL.KV.TYPES 1/56 signed · kit rows: running 20 · timing after route 7 (kv3_hub_Ei, +6) · other flow error 5 (kv3_hg_v1p2, +4) · cancelled (superseded) 3 (kv3_hroot, +2) · kit_rtl 1 (kv3_pv_v6n) · waits on child core 1
- [ ] FAIL.HBM.CORES 89/119 signed · open: no kit-wave row 14 (accel_smh_pt_w, hfd_coll_q3_body_ctl, hgi_sfu_opsa_group1, +9) · running, no result 9 (hfd_coll_q2n2_vm_core, hfd_hgi_vms_glue_nw_t, hgi_coll_tkm_m_tp192__root, +6) · congestion 4 (hgi_sfu_opsa_group0, hnx_vms_bank_q0_faces__vecd4ae, sm_pv_merge) · detail_place 1 (svgr_top) · shape: over cells/util/congestion 1 (hgi_dma_back_static_vp4_banks_cp) · running 1
- [ ] FAIL.HBM.TYPES 1/81 signed · kit rows: waits on child core 33 · running 17 · other flow error 17 (q_b001, +16) · timing after route 8 (NE_iorly, +7) · detail_place 2 (PHY_NW, +1) · cancelled (superseded) 1 (q_spt2) · kit_rtl 1 (q_spb0) · infra (relaunch queued) 1 (q_b102) · congestion 1 (q_su31__physical_v1)
### STALE · unsigned plan cores/types with no live job and no kit-wave row change >= 6 h: 194 (live check: ps/systemd/docker on all hosts, NOT SEEN: intel2; wave state: local copy 11-12 00:31; full list lanes/STALE.tsv)
- [ ] STALE.S81 119 (cores 3, types 116) · by owner: KIT-WAVE-1 115, DIE-S81-85 3, unowned 1
  - core dsdv_bksel_q · no kit-wave row · owner DIE-S81-85
  - core dsdv_gunit_l1f_bf · no kit-wave row · owner DIE-S81-85
  - core s81p_slice_station__t51_ot_s81_station_t51_native_w · no kit-wave row · owner DIE-S81-85
  - type bk_sel__t2 · FAIL route FLOW @ 2026-11-08 08:20 (88.3h) · owner KIT-WAVE-1
  - type serdes__t1__clfe1f0815 · FAIL route INFRA @ 2026-11-08 22:51 (73.8h) · owner KIT-WAVE-1
  - type ot_s81sl_kv_leaf__t1 · CANCELLED geom SUPERSEDED @ 2026-11-09 06:52 (65.8h) · owner KIT-WAVE-1
  - type ot_s81sl_kv_leaf__t3 · CANCELLED geom SUPERSEDED @ 2026-11-09 06:52 (65.8h) · owner KIT-WAVE-1
  - type ot_s81sl_kv_leaf__t4 · CANCELLED geom SUPERSEDED @ 2026-11-09 06:52 (65.8h) · owner KIT-WAVE-1
  - type ot_s81sl_kv_leaf__t5 · CANCELLED geom SUPERSEDED @ 2026-11-09 06:52 (65.8h) · owner KIT-WAVE-1
  - type dsdv_slice_c1x_C__t8 · FAIL place RTL @ 2026-11-09 21:08 (51.5h) · owner KIT-WAVE-1
  - type dsdv_slice_c1x_C__t5 · FAIL place INFRA @ 2026-11-09 23:36 (49h) · owner KIT-WAVE-1
  - type dsdv_slice_c1x_C__t6 · FAIL place RTL @ 2026-11-10 01:18 (47.3h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t17 · FAIL route ROUTING @ 2026-11-10 01:50 (46.8h) · owner KIT-WAVE-1
  - type dsdv_slice_lepw_mus_LP__t2 · FAIL route ROUTING @ 2026-11-10 02:02 (46.6h) · owner KIT-WAVE-1
  - type dsdv_slice_c1x_C__t7 · FAIL place STRUCTURAL @ 2026-11-10 03:50 (44.8h) · owner KIT-WAVE-1
  - type dsdv_slice_c3x_C__t1 · FAIL unit PLAN @ 2026-11-10 04:27 (44.2h) · owner KIT-WAVE-1
  - type svc_hi_dsdv_svc_rs__t1 · CANCELLED kit_rtl RULING @ 2026-11-10 09:40 (39h) · owner KIT-WAVE-1
  - type svc_hi_dsdv_svc_rs__t2 · CANCELLED kit_rtl RULING @ 2026-11-10 09:40 (39h) · owner KIT-WAVE-1
  - type svc_hi_dsdv_svc_rs__t3 · CANCELLED kit_rtl RULING @ 2026-11-10 09:40 (39h) · owner KIT-WAVE-1
  - type svc_hi_dsdv_svc_rs__t4 · CANCELLED kit_rtl RULING @ 2026-11-10 09:40 (39h) · owner KIT-WAVE-1
  - type svc_hi_dsdv_svc_rs__t5 · CANCELLED kit_rtl RULING @ 2026-11-10 09:40 (39h) · owner KIT-WAVE-1
  - type svc_hi_dsdv_svc_rs__t6 · CANCELLED kit_rtl RULING @ 2026-11-10 09:40 (39h) · owner KIT-WAVE-1
  - type svc_lo_dsdv_svc_rs__t1 · CANCELLED kit_rtl RULING @ 2026-11-10 09:40 (39h) · owner KIT-WAVE-1
  - type svc_lo_dsdv_svc_rs__t2 · CANCELLED kit_rtl RULING @ 2026-11-10 09:40 (39h) · owner KIT-WAVE-1
  - type svc_lo_dsdv_svc_rs__t3 · CANCELLED kit_rtl RULING @ 2026-11-10 09:40 (39h) · owner KIT-WAVE-1
  - type svc_lo_dsdv_svc_rs__t4 · CANCELLED kit_rtl RULING @ 2026-11-10 09:40 (39h) · owner KIT-WAVE-1
  - type svc_lo_dsdv_svc_rs__t5 · CANCELLED kit_rtl RULING @ 2026-11-10 09:40 (39h) · owner KIT-WAVE-1
  - type svc_lo_dsdv_svc_rs__t6 · CANCELLED kit_rtl RULING @ 2026-11-10 09:40 (39h) · owner KIT-WAVE-1
  - type svc_lo_dsdv_svc_rs__t7 · CANCELLED kit_rtl RULING @ 2026-11-10 09:40 (39h) · owner KIT-WAVE-1
  - type svc_lo_dsdv_svc_rs_w__t1 · CANCELLED kit_rtl RULING @ 2026-11-10 09:40 (39h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t22 · CANCELLED geom SUPERSEDED @ 2026-11-10 18:30 (30.1h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t29 · CANCELLED geom SUPERSEDED @ 2026-11-10 18:30 (30.1h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t33 · CANCELLED geom SUPERSEDED @ 2026-11-10 18:30 (30.1h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t5 · CANCELLED geom SUPERSEDED @ 2026-11-10 18:30 (30.1h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t67 · CANCELLED geom SUPERSEDED @ 2026-11-10 18:30 (30.1h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t42 · FAIL signoff ROUTING @ 2026-11-10 19:07 (29.5h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t44__clf4ea6d4b · FAIL gen_lint FLOW @ 2026-11-10 19:29 (29.1h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t51 · FAIL preflight FLOW @ 2026-11-10 19:29 (29.1h) · owner KIT-WAVE-1
  - type dsdv_slice_lepe_nh_mus_LP__t1 · FAIL route ROUTING @ 2026-11-10 21:04 (27.6h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t7 · FAIL route ROUTING @ 2026-11-10 21:04 (27.6h) · owner KIT-WAVE-1
  - type serdes__t2 · FAIL route FLOW @ 2026-11-10 21:04 (27.6h) · owner KIT-WAVE-1
  - type iqf__t1 · FAIL signoff TIMING @ 2026-11-10 21:26 (27.2h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t37 · FAIL route ROUTING @ 2026-11-10 21:46 (26.9h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t59 · FAIL route ROUTING @ 2026-11-10 23:05 (25.5h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t34 · FAIL route ROUTING @ 2026-11-10 23:27 (25.2h) · owner KIT-WAVE-1
  - type col_h10_r1__t1__cld01bb4ae · RETRY-INFRA gen_lint INFRA @ 2026-11-10 23:29 (25.1h) · owner KIT-WAVE-1
  - type dsdv_slice_lepw_mu_LP__t2 · CANCELLED geom SUPERSEDED @ 2026-11-10 23:32 (25.1h) · owner KIT-WAVE-1
  - type serdes__t12 · CANCELLED geom SUPERSEDED @ 2026-11-10 23:32 (25.1h) · owner KIT-WAVE-1
  - type serdes__t1__clb45db5be · CANCELLED geom SUPERSEDED @ 2026-11-10 23:32 (25.1h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t25__cl431c660f · CANCELLED geom SUPERSEDED @ 2026-11-10 23:46 (24.9h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t35 · CANCELLED geom SUPERSEDED @ 2026-11-10 23:46 (24.9h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t38 · CANCELLED geom SUPERSEDED @ 2026-11-10 23:46 (24.9h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t6 · CANCELLED geom SUPERSEDED @ 2026-11-10 23:46 (24.9h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t69 · CANCELLED geom SUPERSEDED @ 2026-11-10 23:46 (24.9h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t70 · CANCELLED geom SUPERSEDED @ 2026-11-10 23:46 (24.9h) · owner KIT-WAVE-1
  - type serdes__t15__cla3d02796 · FAIL kit_topology PLAN @ 2026-11-10 23:48 (24.8h) · owner KIT-WAVE-1
  - type slice_station__t24__cl64811a5d · FAIL kit_topology PLAN @ 2026-11-10 23:48 (24.8h) · owner KIT-WAVE-1
  - type slice_station__t49 · CANCELLED gen SUPERSEDED @ 2026-11-10 23:53 (24.7h) · owner KIT-WAVE-1
  - type serdes__t3 · FAIL kit_topology PLAN @ 2026-11-10 23:59 (24.6h) · owner KIT-WAVE-1
  - type serdes__t4 · FAIL kit_topology PLAN @ 2026-11-10 23:59 (24.6h) · owner KIT-WAVE-1
  - type slice_station__t42__clcf44e680 · FAIL kit_topology PLAN @ 2026-11-10 23:59 (24.6h) · owner KIT-WAVE-1
  - type slice_station__t43 · FAIL kit_topology PLAN @ 2026-11-10 23:59 (24.6h) · owner KIT-WAVE-1
  - type svc_hi_dsdv_svc_pvso_entry__t1 · FAIL kit_topology PLAN @ 2026-11-10 23:59 (24.6h) · owner KIT-WAVE-1
  - type ot_s81sl_kv_leaf__t2 · FAIL kit_topology PLAN @ 2026-11-11 00:09 (24.5h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t13 · FAIL kit_topology PLAN @ 2026-11-11 00:09 (24.5h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t4 · FAIL kit_topology PLAN @ 2026-11-11 00:09 (24.5h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t50 · FAIL kit_topology PLAN @ 2026-11-11 00:09 (24.5h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t53__cl958451dd · FAIL kit_topology PLAN @ 2026-11-11 00:09 (24.5h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t61 · FAIL kit_topology PLAN @ 2026-11-11 00:09 (24.5h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t71 · FAIL kit_topology PLAN @ 2026-11-11 00:09 (24.5h) · owner KIT-WAVE-1
  - type serdes__t16 · FAIL kit_topology PLAN @ 2026-11-11 00:09 (24.5h) · owner KIT-WAVE-1
  - type svc_hi_dsdv_svc_pvso_entry__t2 · FAIL kit_topology PLAN @ 2026-11-11 00:09 (24.5h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t23 · FAIL kit_topology PLAN @ 2026-11-11 00:20 (24.3h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t24__cl81374cd8 · FAIL kit_topology PLAN @ 2026-11-11 00:20 (24.3h) · owner KIT-WAVE-1
  - type dsdv_slice_c1x_C__t1 · RETRY-INFRA gen_lint INFRA @ 2026-11-11 00:45 (23.9h) · owner KIT-WAVE-1
  - type dsdv_slice_c1x_C__t10 · RETRY-INFRA gen_lint INFRA @ 2026-11-11 00:45 (23.9h) · owner KIT-WAVE-1
  - type dsdv_slice_c1x_C__t3 · RETRY-INFRA kit_topology INFRA @ 2026-11-11 00:45 (23.9h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t10 · FAIL kit_topology PLAN @ 2026-11-11 00:42 (23.9h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t27 · RETRY-INFRA kit_topology INFRA @ 2026-11-11 00:45 (23.9h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t3 · FAIL kit_topology PLAN @ 2026-11-11 00:42 (23.9h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t15 · FAIL kit_topology PLAN @ 2026-11-11 00:54 (23.7h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t36 · FAIL kit_topology PLAN @ 2026-11-11 00:54 (23.7h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t60 · FAIL kit_topology PLAN @ 2026-11-11 00:54 (23.7h) · owner KIT-WAVE-1
  - type slice_station__t52 · FAIL kit_topology PLAN @ 2026-11-11 00:54 (23.7h) · owner KIT-WAVE-1
  - type slice_station__t6__cl0755c26e · FAIL kit_topology PLAN @ 2026-11-11 01:06 (23.5h) · owner KIT-WAVE-1
  - type dsdv_slice_c1x_C__t9 · RETRY-INFRA preflight INFRA @ 2026-11-11 01:32 (23.1h) · owner KIT-WAVE-1
  - type dsdv_slice_lepe_mu_C__t1 · RETRY-INFRA gen INFRA @ 2026-11-11 01:32 (23.1h) · owner KIT-WAVE-1
  - type dsdv_slice_lepe_nh_mus_C__t1 · RETRY-INFRA kit_topology INFRA @ 2026-11-11 01:32 (23.1h) · owner KIT-WAVE-1
  - type dsdv_slice_lepw_mu_C__t1 · RETRY-INFRA kit_rtl INFRA @ 2026-11-11 01:32 (23.1h) · owner KIT-WAVE-1
  - type dsdv_slice_lepw_mus_C__t1 · RETRY-INFRA gen_lint INFRA @ 2026-11-11 01:32 (23.1h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t40__cl86ea32b3 · RETRY-INFRA kit_topology INFRA @ 2026-11-11 01:32 (23.1h) row ot_s81sl_leaf__t40__cl86ea32b3__sid5S · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t40__cl86ea32b3__sid5S · RETRY-INFRA kit_topology INFRA @ 2026-11-11 01:32 (23.1h) · owner unowned
  - type ot_s81sl_leaf__t43 · RETRY-INFRA kit_topology INFRA @ 2026-11-11 01:32 (23.1h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t68 · RETRY-INFRA kit_topology INFRA @ 2026-11-11 01:32 (23.1h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t74 · RETRY-INFRA kit_rtl INFRA @ 2026-11-11 01:32 (23.1h) · owner KIT-WAVE-1
  - type serdes__t13 · RETRY-INFRA kit_rtl INFRA @ 2026-11-11 01:44 (22.9h) · owner KIT-WAVE-1
  - type serdes__t15__cla2127225 · RETRY-INFRA kit_topology INFRA @ 2026-11-11 01:54 (22.7h) · owner KIT-WAVE-1
  - type slice_station__t36 · RETRY-INFRA kit_topology INFRA @ 2026-11-11 01:54 (22.7h) · owner KIT-WAVE-1
  - type col_h9_r0_p5__t1 · RETRY-INFRA gen_lint INFRA @ 2026-11-11 02:24 (22.2h) · owner KIT-WAVE-1
  - type col_h9_r0_p6__t1 · RETRY-INFRA gen_lint INFRA @ 2026-11-11 02:24 (22.2h) · owner KIT-WAVE-1
  - type dsdv_slice_c1x_C__t4 · RETRY-INFRA preflight INFRA @ 2026-11-11 02:35 (22h) · owner KIT-WAVE-1
  - type col_h10_r0_p4__t1 · FAIL gen FLOW @ 2026-11-11 07:13 (17.4h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t54__cl501e5681 · FAIL gen FLOW @ 2026-11-11 07:13 (17.4h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t16 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-11 16:40 (8h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t24__cl2456157b · CANCELLED geom QUEUE-CANCELLED @ 2026-11-11 16:40 (8h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t25__cl55642d17 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-11 16:40 (8h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t26 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-11 16:40 (8h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t31 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-11 16:40 (8h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t32 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-11 16:40 (8h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t40__clf8bbdae1 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-11 16:40 (8h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t41 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-11 16:40 (8h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t44__clf6cf8492 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-11 16:40 (8h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t47 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-11 16:40 (8h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t53__clb66fa5cb · CANCELLED geom QUEUE-CANCELLED @ 2026-11-11 16:40 (8h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t54__cl706d9749 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-11 16:40 (8h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t55 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-11 16:40 (8h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t57 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-11 16:40 (8h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t58 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-11 16:40 (8h) · owner KIT-WAVE-1
  - type ot_s81sl_leaf__t73 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-11 16:40 (8h) · owner KIT-WAVE-1
- [ ] STALE.HEAD 3 (cores 0, types 3) · by owner: KIT-WAVE-1 3
  - type hd_spn · FAIL signoff TIMING @ 2026-11-09 12:07 (60.5h) · owner KIT-WAVE-1
  - type hd_serdes · RETRY-INFRA place INFRA @ 2026-11-10 01:07 (47.5h) · owner KIT-WAVE-1
  - type hd_ctl · CANCELLED geom QUEUE-CANCELLED @ 2026-11-11 16:40 (8h) · owner KIT-WAVE-1
- [ ] STALE.QC 26 (cores 0, types 26) · by owner: KIT-WAVE-1 24, DIE-QC-97 2
  - type slw_stm_v2__cl9beb65e6 · SUPERSEDED route SUPERSEDED @ 2026-11-07 06:57 (113.7h) · owner KIT-WAVE-1
  - type coll_ftm · WAIT-PARENT queue @ 2026-11-07 23:55 (96.7h) · owner KIT-WAVE-1
  - type coll_core · CANCELLED geom SUPERSEDED @ 2026-11-08 10:30 (86.1h) · owner KIT-WAVE-1
  - type coll_ucie · SUPERSEDED route SUPERSEDED @ 2026-11-08 10:30 (86.1h) · owner KIT-WAVE-1
  - type sle_stm_v3 · SUPERSEDED signoff SUPERSEDED @ 2026-11-09 02:37 (70h) · owner KIT-WAVE-1
  - type sle_stm_v2__cl7b3062fa · SUPERSEDED signoff SUPERSEDED @ 2026-11-09 06:18 (66.3h) · owner KIT-WAVE-1
  - type coll_s · SUPERSEDED signoff SUPERSEDED @ 2026-11-09 08:36 (64h) · owner KIT-WAVE-1
  - type slw_st_b_v1__cle6023ec2 · SUPERSEDED signoff SUPERSEDED @ 2026-11-09 08:36 (64h) · owner KIT-WAVE-1
  - type native59 · FAIL queue RTL @ 2026-11-09 13:33 (59.1h) · owner KIT-WAVE-1
  - type slw_stm_v1__cl05fc43f7__cl2086fa2c · SUPERSEDED signoff SUPERSEDED @ 2026-11-09 14:38 (58h) · owner DIE-QC-97
  - type slw_stm_v1__cl05fc43f7__cl389df4e9 · SUPERSEDED signoff SUPERSEDED @ 2026-11-09 15:36 (57h) · owner DIE-QC-97
  - type slw_stm_v3 · SUPERSEDED signoff SUPERSEDED @ 2026-11-09 17:51 (54.8h) · owner KIT-WAVE-1
  - type glue · FAIL queue RTL @ 2026-11-09 19:31 (53.1h) · owner KIT-WAVE-1
  - type slw_st_b_v1__cl6357f1cc · SUPERSEDED signoff SUPERSEDED @ 2026-11-09 20:07 (52.5h) row slw_st_b_v1__cl6357f1cc__pvffd43fdc · owner KIT-WAVE-1
  - type slw_st_b_v2 · SUPERSEDED signoff SUPERSEDED @ 2026-11-09 21:29 (51.1h) row slw_st_b_v2__pva66d0f22 · owner KIT-WAVE-1
  - type tt_ctlm · FAIL route TIMING @ 2026-11-10 02:13 (46.4h) · owner KIT-WAVE-1
  - type cbf_q00_s2 · SUPERSEDED route SUPERSEDED @ 2026-11-11 02:52 (21.8h) · owner KIT-WAVE-1
  - type sle_stm_v2__cl55be2264 · CANCELLED geom SUPERSEDED @ 2026-11-11 07:45 (16.9h) · owner KIT-WAVE-1
  - type slw_su_l1__cla2a78701 · SUPERSEDED kit_rtl SUPERSEDED @ 2026-11-11 07:45 (16.9h) · owner KIT-WAVE-1
  - type slw_stm_v1__cle34a73c3 · CANCELLED geom SUPERSEDED @ 2026-11-11 07:59 (16.6h) · owner KIT-WAVE-1
  - type slw_stm_v2__cl1ca9c415 · CANCELLED geom SUPERSEDED @ 2026-11-11 07:59 (16.6h) · owner KIT-WAVE-1
  - type slw_su_l1__clcc9d0155 · SUPERSEDED kit_rtl SUPERSEDED @ 2026-11-11 07:59 (16.6h) · owner KIT-WAVE-1
  - type coll_ft__cl78c7b300 · FAIL gen FLOW @ 2026-11-11 08:21 (16.3h) · owner KIT-WAVE-1
  - type sle_su_l1__clc6d66f5b · SUPERSEDED kit_topology SUPERSEDED @ 2026-11-11 08:21 (16.3h) · owner KIT-WAVE-1
  - type coll_ftc · FAIL signoff TIMING @ 2026-11-11 11:25 (13.2h) · owner KIT-WAVE-1
  - type sle_fe_v3 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-11 16:40 (8h) · owner KIT-WAVE-1
- [ ] STALE.KV 24 (cores 0, types 24) · by owner: KIT-WAVE-1 19, unowned 4, DIE-KV-97 1
  - type kv3_hgi_v4 · SUPERSEDED route SUPERSEDED @ 2026-11-05 17:42 (150.9h) · owner KIT-WAVE-1
  - type kv3_hgi_v8 · RETRY-INFRA kit_rtl INFRA @ 2026-11-06 22:42 (121.9h) · owner KIT-WAVE-1
  - type kv3_hgi_v5 · SUPERSEDED route SUPERSEDED @ 2026-11-09 14:57 (57.7h) · owner KIT-WAVE-1
  - type kv3_sys_SD · SUPERSEDED route SUPERSEDED @ 2026-11-09 18:56 (53.7h) · owner KIT-WAVE-1
  - type kv3_pv_v2n · SUPERSEDED place SUPERSEDED @ 2026-11-10 00:31 (48.1h) · owner DIE-KV-97
  - type kv3_pv_v2 · SUPERSEDED place SUPERSEDED @ 2026-11-10 00:44 (47.9h) · owner KIT-WAVE-1
  - type kv3_pv_v3 · SUPERSEDED place SUPERSEDED @ 2026-11-10 00:56 (47.7h) · owner KIT-WAVE-1
  - type kv3_pv_v4 · SUPERSEDED place SUPERSEDED @ 2026-11-10 00:56 (47.7h) · owner KIT-WAVE-1
  - type kv3_io_ft_v1 · FAIL signoff TIMING @ 2026-11-10 08:37 (40h) · owner KIT-WAVE-1
  - type kv3_hgi_v6 · SUPERSEDED gen SUPERSEDED @ 2026-11-10 13:25 (35.2h) · owner KIT-WAVE-1
  - type kv3_pv_v1 · SUPERSEDED kit_rtl SUPERSEDED @ 2026-11-10 17:47 (30.8h) · owner KIT-WAVE-1
  - type kv3_pv_v12 · SUPERSEDED kit_rtl SUPERSEDED @ 2026-11-10 17:47 (30.8h) · owner KIT-WAVE-1
  - type kv3_pv_v1n · SUPERSEDED kit_rtl SUPERSEDED @ 2026-11-10 17:47 (30.8h) · owner unowned
  - type kv3_pv_v3n · SUPERSEDED kit_rtl SUPERSEDED @ 2026-11-10 17:47 (30.8h) · owner unowned
  - type kv3_pv_v4n · SUPERSEDED kit_rtl SUPERSEDED @ 2026-11-10 17:47 (30.8h) · owner unowned
  - type kv3_pv_v6n · FAIL kit_rtl FLOW @ 2026-11-10 17:47 (30.8h) · owner unowned
  - type kv3_hgi_v3 · SUPERSEDED gen SUPERSEDED @ 2026-11-11 05:15 (19.4h) · owner KIT-WAVE-1
  - type kv3_pv_v7 · SUPERSEDED gen_lint SUPERSEDED @ 2026-11-11 07:13 (17.4h) · owner KIT-WAVE-1
  - type kv3_pv_v5 · SUPERSEDED gen SUPERSEDED @ 2026-11-11 11:06 (13.5h) · owner KIT-WAVE-1
  - type kv3_phy_v1 · FAIL signoff TIMING @ 2026-11-11 11:16 (13.4h) · owner KIT-WAVE-1
  - type kv3_pv_v6 · FAIL gen FLOW @ 2026-11-11 11:16 (13.4h) · owner KIT-WAVE-1
  - type kv3_pv_v8 · SUPERSEDED gen SUPERSEDED @ 2026-11-11 11:16 (13.4h) · owner KIT-WAVE-1
  - type kv3_phy · FAIL signoff TIMING @ 2026-11-11 11:25 (13.2h) · owner KIT-WAVE-1
  - type kv3_io_cor · FAIL signoff TIMING @ 2026-11-11 11:46 (12.9h) · owner KIT-WAVE-1
- [ ] STALE.HBM 22 (cores 15, types 7) · by owner: KIT-WAVE-1 10, HBM-CORES-B 7, unowned 3, AUTO-RESIGN 1, DIE-HBM-98 1
  - core ot_hbm_sm_kv_line · no kit-wave row · owner HBM-CORES-B
  - core ot_hbm_su_pg_lane1p_core · no kit-wave row · owner AUTO-RESIGN
  - core ot_hfd_coll_q3_body_ctl · no kit-wave row · owner HBM-CORES-B
  - core ot_hgi_sfu_opsa_group1 · no kit-wave row · owner HBM-CORES-B
  - core ot_hgi_sfu_opsb_group · no kit-wave row · owner HBM-CORES-B
  - core ot_hgi_sfu_split3_ctl_rest_1c · no kit-wave row · owner HBM-CORES-B
  - core ot_q2nf_rest · no kit-wave row · owner HBM-CORES-B
  - core ot_wbq_sw · no kit-wave row · owner HBM-CORES-B
  - core ot_hfd_coll_q2n2_vm_core · FAIL route TIMING @ 2026-11-03 17:21 (199.3h) · owner KIT-WAVE-1
  - core ot_hgi_dma_back_static_vp4_banks_cp · SUPERSEDED route SUPERSEDED @ 2026-11-04 08:58 (183.7h) · owner KIT-WAVE-1
  - core ot_hgi_coll_tkm_m_tp192__root · SUPERSEDED queue SUPERSEDED @ 2026-11-07 11:17 (109.3h) · owner KIT-WAVE-1
  - core ot_hbm_idx_topk_link_static · FAIL place FLOW @ 2026-11-07 19:38 (101h) · owner KIT-WAVE-1
  - type q_spt2 · CANCELLED geom SUPERSEDED @ 2026-11-09 00:40 (72h) · owner KIT-WAVE-1
  - type q_spb1 · FAIL signoff TIMING @ 2026-11-09 01:06 (71.5h) · owner KIT-WAVE-1
  - type vsN1 · FAIL signoff TIMING @ 2026-11-09 01:20 (71.3h) · owner KIT-WAVE-1
  - type vsN5 · FAIL signoff TIMING @ 2026-11-10 11:56 (36.7h) · owner KIT-WAVE-1
  - type vsN2 · FAIL signoff TIMING @ 2026-11-10 14:15 (34.4h) · owner KIT-WAVE-1
  - type vsN6 · FAIL signoff TIMING @ 2026-11-10 20:52 (27.8h) · owner KIT-WAVE-1
  - core ot_hgi_sfu_opsa_group0 · FAIL route ROUTING @ 2026-11-10 21:57 (26.7h) · owner unowned
  - core hnx_fused_lane_c · FAIL signoff TIMING @ 2026-11-10 22:07 (26.5h) · owner unowned
  - type q_mcb · SUPERSEDED kit_rtl SUPERSEDED @ 2026-11-10 23:59 (24.6h) · owner DIE-HBM-98
  - core ot_svgr_top · FAIL place PLAN @ 2026-11-11 07:45 (16.9h) · owner unowned
<!-- BREAKDOWN END -->

## EDIT · rules
- PENDING items only, one short line each, edited in place. Remove an item when done (evidence goes in PATH-FREEZE.md / lane files).
- Line form: `- [ ] ID task · OWNER · STATUS · current fact → DEP.ID` ; "→ X" means this item waits on X (each → is a link).
- Gate ids per die are PFX.INFRA / PFX.GRT / PFX.CLK / PFX.BIND / PFX.STA.
- OWNER 12.18 (2026-10-29 05:44 PDT): full-gate census per die -> lanes/CLOSURE-LIST.tsv (fixed list); rule freeze (new checks only by owner); hourly burn-down open/closed/added; all 5 dies in parallel.
- OWNER 12.17 (2026-10-29 05:31 PDT): freeze plan on die GRT0+clock pass (fix-only after); one clock tool ot_clk.py for all dies; 2 parallel fix variants per failing gate; strict bind clean before GRT counts.
- DIE METHOD = METHODOLOGY s12 v5.1 (v5.0: early taps = macro insertion balancing, AOCV 0.21%/mm gates; v5.1: trims/useful skew/pads sparse <=~5% + CLOCK-RESIDUAL ledger after structural fix; 5%/15% cost = targets) (OWNER 10-26, frozen; change only on measured failure + owner decision): 12.7 MASTER PLAN FIRST per die (census -> corridors <=0.6 -> bays <=405 um every path/layer -> M7 entry pins -> worst-case PG, PG-shielded clock, islands clock/reset only, one core latency) + static plan gates incl. analytic predictor BEFORE any block build; kits carry a plan slice. 12.8 clock by construction: plan-defined centre clock entry per core, 250 ps TT, structured core trees; NO early taps / post-measurement trims / clock ECOs / mesh-node CPPR (plan-computed per-tap sizing OK). Freeze = GRT0 incl clock (>=50 it) + DIE STA with the real clock on related pairs (TT setup, FF hold; CPPR to last tree node); 80 ps skew = design target only. v4.6-4.9: MSCTS H-tree->ONE continuous mesh (signed mesh = CPPR point)->short local trees; clock OCV = depth/distance table (draft, owner review); droop shared (clock charged differential only); data hold buffers allowed. 12.9: one owner per die plan/clock (lanes/OWNERS-DIE.md); gate numbers via NUMBER-CHECK.
- Release gate = die STA on real views + token pass.
- Status words: RUNNING WAITS TODO NEW COORD OWNER FAIL PASS FROZEN BLOCKED NOT RUN.

## DIE s81 · S81 · rev plan_h2_2249 + RF1 · FROZEN (one-block fixes) · count 47/57 + 4/205 types at 06:05
- [ ] S81.PROUTE Station safe form (OWNER 11-02 pilot + 11-03 safe forms) · S81 / S81-PROUTE-2 (DIE-S81-65) · RUNNING · MAIN = FIXED-BAY: relay flop + negative-level lockup latch + repeater bays pre-placed <=405 um, local leaf per bay, per-hop delay/slew/hold computed before route; parent-route kit p7S_x11 (GEN_LINT + PREFLIGHT PASS) kept only as comparison; result applies to QC stations as one class
- [ ] S81.BIND Strict native bind · S81 / DIE-S81-65 · PASS · event2 completed 11:40:42; 398 partitions / 204 types / 873 crossings / 606281 bits, connectivity errors 0; this is not a routing pass
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kits sign; hold gate now >= 0 (OWNER 11-02) → S81.TILES
- [ ] S81.GRT Whole-data-die global routing · S81 / DIE-S81-65 · NOT RUN · no qualified current all-partition signal+clock GRT receipt → S81.TILES → S81.PARENT
- [ ] S81.STA Complete die TT setup / FF hold on real views · S81 / DIE-S81-65 · BLOCKED · retained partial run: TT +31.30, measured FF +10.75 on 65420 pairs; 747728 hold pairs unmeasured; current full-die propagated STA absent → S81.GRT → S81.TILES
- [ ] S81.TILES Required current child / partition views · S81 / KIT-WAVE · RUNNING · cap B route/finish/RCX DRC0 ANT0, 748 pins preserved, final signoff+ownEQ next; L2M repaired route clean, final gates pending; Xfin relief GRT still running after prior202overflow
- [ ] S81.PARENT Production parent composition · S81 · BLOCKED · QBS SYNTH reached but nine exact selected hard-child implementation/model joins missing; PINCOPY histogram parent proof+GPL running, child signed/EQ1866 does not qualify parent → S81.TILES
- [ ] S81.T41 Forwarded data/K timing witness · S81 / GEOM · WAITS · corrected A/B only placed; default-OFF observer ready4b96673bc; one baseline-A CTS+witness needs review, old GRT4750 remains FAIL → INFRA.REVIEW
- [ ] S81.RESET SerDes warm-reset sequencer implementation · S81+HEAD / DIE-S81-65 + DIE-HEAD-71 · RUNNING · OWNER 11-02 17:55 closed the choice: local sequencer holds reset >=64 rck edges after PMA clock restart, no running-clock promise; shared module adoption on S81 in progress (helper reset) → READY

## DIE s81_head · HEAD · rev l48un (main l48ui + hd_serdes data_inputs, COORD 11-07 09:4x; counted against l48un) · count 4/4 + 12/25 types at 06:05
- [ ] HEAD.BIND Current parent source / child-model composition · HEAD / DIE-HEAD-71 · BLOCKED · exact current source+views must compose before full parent release → HEAD.TILES
- [ ] HEAD.CLK Current die clock qualification · HEAD / DIE-HEAD-71 · BLOCKED(kits) · clock proof l48w_sth GRT0/TT+252.75 stands (older pass counts); l48w_sth GRT0/TT+252.75/START0of1607; only2 real core views,0 kits plus declared budgets; 530106 hold pairs unmeasured, not current full-die timing → HEAD.TILES
- [ ] HEAD.GRT Current whole-die signal+clock global routing · HEAD / DIE-HEAD-71 · BLOCKED · retained infrastructure routing is not a complete current parent data-route receipt → HEAD.TILES → HEAD.BIND
- [ ] HEAD.STA Complete current parent TT/FF and seam timing · HEAD / DIE-HEAD-71 · BLOCKED · actual all-bit parent interface/hold qualification absent → HEAD.GRT → HEAD.TILES
- [ ] HEAD.SERDES kp4 e13a own routed equivalence · HEAD / SIGNOFF-SPRINT-19 · RUNNING · n-head SIGNED TT+2.48 FF+11.85 DRC0 ANT0 faceguardPASS; existing own routedLEC CPU-active, await actualEQ before count
- [ ] HEAD.TILES Current partition physical closure · HEAD / KIT-WAVE · RUNNING · STmD route DRC0/antenna0, finishRCX/signoff+EQ pending; original tile/spine/HOST repairs continue; current HOST timing/DRV/neck and meshFF-104.83 unresolved → HEAD.SERDES
- [ ] HEAD.HOSTLEC Current routed HOST qualification · HEAD · WAITS · retained component136216EQ complete; newer routedb2 is a different subject and still needs its own proof+physical closure → HEAD.TILES
- [ ] HEAD.SEAM Mesh sender/receiver timing contract · HEAD · BLOCKED · finite hold repair hits setup-versus-hold feasibility; any seam rebudget needs actual peer and parent TT/FF qualification, no constraint relaxation → HEAD.STA

## DIE qwen_compute · QC · rev plan_qc52 + CA+1 + y-shrink2 · count 14/19 at 06:05
- [ ] QC.BIND Strict native bind · QC / DIE-QC-81 · PASS · 119 types / 377 parts,0 errors; G0C completeness remains FAIL11
- [ ] QC.CLK Native die clock implementation · QC / DIE-QC-81 · BLOCKED · 51596 planned cells / 10929 taps sourcegeometryPASS; native prefix is unexecuted, no parent PG/GRT/RC/STA or START-freeze credit → QC.CLOCKPREFIX → QC.TILES
- [ ] QC.CLOCKPREFIX Bounded native clock import/access diagnostic · QC · WAITS · exact current homes/aliases reviewed; staged64GB8T geometry-only import, no legalization/GRT/STA; awaits root scoped release → INFRA.REVIEW
- [ ] QC.GRT Whole-die signal+clock global routing · QC / DIE-QC-81 · BLOCKED · no current whole-die GRT pass → QC.TILES → QC.GLUE → QC.CLK
- [ ] QC.STA Propagated whole-die TT setup / FF hold · QC / DIE-QC-81 · BLOCKED · no complete current parent STA; count-alignment or child timing is not die timing → QC.GRT → QC.TILES
- [ ] QC.TILES Qualified partitions and capacity · QC / KIT-WAVE · RUNNING · Q4 official177206EQ complete; all8SU pre-routeEQ complete; L1 finalGRT TT-14.64 FF-2.52, three-edit PLACE coupon pending; required unsigned views remain
- [ ] QC.SC SC source+clock-count event and first physical closure · QC / DIE-QC-81 · RUNNING · OWNER 11-02 ADOPTED (EQ/sim-gated; 8 SC types >400k cells need CORE-KS split); actual336662std / wholeEQ55664; sharing changes default-mode FF43058→42671, so not dormant; corrected572bit legal-trackGEN+LOOK passes, first PLACE awaits review; chain-end variants require separate handling → OWNER.SOURCE
- [ ] QC.RED RED source/parent event and clock implementation · QC · BLOCKED · actualPLACE225665std/34225FF/40.268%fill; same8269node sink rebind max15.77um is planning only; root/common-frame and parent+1 event unqualified → OWNER.SOURCE
- [ ] QC.STM Current native STM qualification · QC · RUNNING · corrected slw_v3 GEN17874contactsPASS, ordinarySYNTH→PLACE queued; two additional exact source/count matches224247/222702std, other distinct types still incomplete
- [ ] QC.GLUE Joint parent/interface geometry event · QC / DIE-QC-81 · RUNNING · OWNER 11-02 ADOPTED (EQ-gated; pipeline stages for 1838>1110 um reach); coordinate coupon legal but5306long reaches remain; fixedSTART1838um exceeds1110um reach budget; compact proposal leaves1088.64um parent gap and missing west peers → OWNER.SOURCE
- [ ] QC.NL Corrected clock-inclusive GRT probe · QC · WAITS · prior attempt failed MM context before FF; same-byte4_cts alias+configuredmargin10 fixture passes, one bounded retry awaits root → INFRA.REVIEW

## DIE qwen_kvsys · KV · rev plan_c (32) + RF-KV1, event on main · count 24/32 at 06:05
- [ ] KV.BIND Current strict native bind · KV / DIE-KV-79 · PASS · source connectivity passes; no physical die credit
- [ ] KV.CLK Complete current real-view clock timing · KV / DIE-KV-79 · BLOCKED(kits) · clock proof stands (older pass counts): mix TT+595.71/CA0of3595 has7coreviews,0kits plus budgets; FF37674pairs NULL/unmeasured → KV.TILES
- [ ] KV.GRT Current whole-die global routing · KV / DIE-KV-79 · NOT RUN · latest parent macro-fit vehicle explicitly dieGRT/route NOTRUN; reported zero-overflow successes are partition/core probes → KV.TILES → KV.HROOT → KV.HG
- [ ] KV.STA Current whole-die propagated TT/FF · KV / DIE-KV-79 · BLOCKED · no complete routed current-die timing receipt → KV.GRT → KV.CLK
- [ ] KV.TILES Required hard-child and partition closure · KV / KIT-WAVE · RUNNING · EX70 SIGNED+own20490EQ publishedHG-only; PCfMX GRT0 now timing/repair, AHUB/PV/PHY and HR source-follow work remain
- [ ] KV.HG HG native9-child qualification and parent geometry · KV · RUNNING · parentSYNTH189754std+30macros; q1 currentgold→actualfinal proof admitted normally; six current views need reconstruction,1057bit corridor still needs placed endpoints/shared-demand reservations → KV.TILES
- [ ] KV.HROOT Parent geometry/reset source event · KV / DIE-KV-79 · RUNNING · OWNER 11-02 ADOPTED (EQ-gated; retiming/pipeline for 2192>1920 um); fixed separation2192.120um exceeds1920um bound by272.120; reset repoint has real observer counterexample; local placement cannot close → OWNER.SOURCE
- [ ] KV.FORMAL CTL/HHP/RX native closure · KV · RUNNING · CTL123diff, HHP5persistent enabled/unreset-state failures; RX native+emitted17769EQ, mapped gate pending; complete new proof-helper bundle waits publication → INFRA.MERGE
- [ ] KV.RECIP Compact RECIP and ZH physical qualification · KV · WAITS · RECIP GRT TT+161.66 FF+9.67 but actualfill15.27/empty68.78 FAIL; ZH actualfill45.589 and independentLOOK supports one PLACE diagnostic → INFRA.REVIEW
- [ ] KV.FN Production token execution · KV / TOK · RUNNING · sole correctGEN1 probe fault0, nofirstcal; observed~2.3cycles/s implies~35h for290307-cycle window at that rate, not measured token throughput → TOK.QW

## DIE hbm · HBM · rev d44v_por (parts 1-7) · count 37/95 at 06:05
- [ ] HBM.BIND Qualified current native production composition · HBM / DIE-HBM-76 · BLOCKED · native source/pin/profile and clock/START joins incomplete; historical wrapped bindings do not qualify current production → HBM.CLK → HBM.TILES
- [ ] HBM.HUBMESH Hub mesh / production clock integration · HBM / DIE-HBM-76 · STRUCTURAL PASS, BLOCKED(kits) · hub mesh a3e6s, NE_v2, die TT +93.69, CA 773/773 (hold margin 0); next: plan event d44v (q3_edge single-column slot, pslice_c5 2.6-um macro channels, xload ctlx, hnx fused) -> kits -> real-view hold
- [ ] HBM.CLK Native clock/source/PG composition · HBM / DIE-HBM-76 · BLOCKED · 21 station types planned3077ports pass consumer/S0parity;283plannedhomes,260sourcehomes(16mismatch),23missing; active-role/native pin/net/START joins remain unqualified
- [ ] HBM.GRT Complete current die global routing · HBM / DIE-HBM-76 · BLOCKED · planned station/clock repairs and historical wrapped probes do not establish joint current signal+clock GRT → HBM.CLK → HBM.TILES
- [ ] HBM.STA Complete current die real-view TT/FF · HBM / DIE-HBM-76 · BLOCKED · actual native child models and propagated production clock/parent timing incomplete → HBM.GRT → HBM.TILES
- [ ] HBM.TILES Current native source / physical qualification · HBM / KIT-WAVE · RUNNING · native VMS11560EQ, BFQG8650EQ, Tnode4730EQ; historic wrapped shell signoffs cannot substitute current native views
- [ ] HBM.PSLICE Corrected reset source integration and physical plan · HBM / DIE-HBM-76 · WAITS · legacybridge4419751comparisonsPASS, native4EQ108839; +24resetFF/0missioncycles, ready96b0c0184; fresh physical locality/fill still open → INFRA.MERGE
- [ ] HBM.PSTORE Native placement closure · HBM / DIE-HBM-76 · RUNNING ·70580EQ;51guides bind; priorGPLdiverged, sole unchanged-sourcephi1.01cached retry active; actualfreefill4.534% remains explicit
- [ ] HBM.QUERY Current head5 native equivalence · HBM / DIE-HBM-76 · RUNNING · face1622PASS; fresh native4 fullproof31379EQ/0diff with171hints, wrong-polarity control running; source/caller/clock event still PREP, no physical release
- [ ] HBM.TNODE Compact native parent event · HBM / DIE-HBM-76 · WAITS · oldactualfill6.57/empty83.41FAIL; compact125.28×95.04 preserves1341pins and30worldclock/PG positions, parentDATAevent+GEN/LOOK required → OWNER.SOURCE
- [ ] HBM.OPSTORE Native frontend/source cut · HBM / HBM-CORES-KITS-40 · BLOCKED · escaped-identifier frontend failure diagnosed; no wrapped-view alias or physical credit

## TOKEN · Token-pass gate per design
- [ ] TOK.DS DeepSeek whole-die token execution · TOK / S81 · RUNNING · whole-die frontend builds active; nativeSRAM16checkpointwords bothbanks PASS and CAP-safe representative fieldPASS, production mission not qualified → TOK.PROGRAM → S81.STA → HEAD.STA
- [ ] TOK.QW Qwen QC+KV token execution · TOK / KV · RUNNING · actual512XAwords4users pass livecalendar/nativeSU; HEAD stage has zeroSUops and weights/programme not installed in native form; KV solebootprobe not whole-token pass → TOK.PROGRAM → QC.STA → KV.STA
- [ ] TOK.PROGRAM Native arithmetic / programme / leases · TOK · RUNNING · ROOT arithmetic64GB build active, monitorXA live replayPASS, DSglobaldates/leases and HEADprogramme integration open; component transport is not full mission
- [ ] TOK.HBM Production HBM token execution · TOK / HBM · BLOCKED · historical accepted~1677tok/s remains scoped; current SOURCE11 frontend64GB/J2 MEMCG-OOM, one96GB/J1 checkpoint-resume queued normally; S0/S3 producers/packing/alignedstaging and visibility still open → HBM.STA
- [ ] TOK.E2E End-to-end token pass · TOK · NOT RUN · requires actual complete numerical/programme execution and qualified die timing → TOK.DS → TOK.QW → TOK.HBM

## FLOW · Flow release + workflow (OWNER 12.27)
- [ ] FLOW.KITS Current type-kit closure · KITS_FLOW / KIT-WAVE · RUNNING · collect/relaunch shared postCTS helper failures with complete pinned bundles; 17:20 coordinator reported core_clock_band staging crash, deployment/recovery must be collected before credit
- [ ] FLOW.CTS Retained CTS runtime portability · KITS_FLOW / S81 · WAITS · firstR1 failed beforeCAD on shallowcore_flow import; narrowfixf34267628 has42tests+actualcontainerpre-make smokePASS; sole dispatcher retry after review, R2separateheld → INFRA.REVIEW
- [ ] FLOW.COUNT Exact SIGNED+ownEQ / current-model counts · SIGNOFF-SPRINT · RUNNING · prior reported count50 differs from generated cache; neither is a fresh recount; e13a timingSIGNED waits ownEQ; EX70 HG-only child closure does not release parent

## INFRA · Merge, hosts, disks
- [ ] INFRA.MERGE Publish clean gated source/tool trains · ROOT-MERGE-24 · RUNNING · main 48c37eca7d3 (F5 QC red/HBM POR/TOK-QW-4/KV/S81 lnland/TOK-DS-4, F6 HEAD headgate, F7 TOK-HBM d44u); next: kw-fix-3-s81pf 4a2dae0f548, kw-fix-2 d483825fd6e (class R), die-kv-62-stations 7bbad22d032; FLOW-24 candidate RSZ-3006/RSZ-0074 286030c4f4
- [ ] INFRA.REVIEW Release concrete reviewed next steps · ROOT · RUNNING · retainedCTSfix/retry, QCnativeclockprefix, T41witness, NLcorrectedprobe, ZHPLACE and compactTnodeGEN; actualLOOK/source/reset/count scope before physical dispatch
- [ ] INFRA.DISK Scratch headroom · PRUNE-1103A · RUNNING · 04:3x free: intel2 251 GB (93%, was 63 GB 04:0x; released kit attempts + canary sources, Codex dirs MOVED to epyc2 root), intel1 207 GB (95%), epyc2 scratch2 324 GB; epyc2 root 1.3 TB (keep >=500); target >=300 each
- [ ] INFRA.LOAD Queue/build turnaround · KITS_FLOW / TOK · RUNNING · onlyepyc2/intel1/intel2 active; conserve progressing jobs, no duplicate proof/build; whole-hierarchy OOM and serial simulation are real schedule risks

## OWNER · Explicit contract decisions
- [x] OWNER.RESET Resolve soft SerDes reset authority · OWNER · DONE · OWNER 11-02: local >=64-edge reset sequencer; running-clock guarantee or priced safe local sequencer; no blanket reset extension; plain question logged, other work continues
- [x] OWNER.SOURCE Price coupled source/clock/count/parent changes · OWNER / ROOT · DONE · OWNER 11-02: SC/RED/GLUE/HROOT + compact native events adopted as explicit EQ-gated plan events; HBM unfrozen; Qwen stage37 adopted; SC default-mode sink change, RED parent event, GLUE/Hroot repack and compact native events require explicit adoption; no silent plan activation

## WAITS · who
### Waiting on the owner
- OWNER.RESET: soft SerDes stopped-PMA warm-reset guarantee or priced safe sequencer; no blanket4→64 reset assumption. Plain questions in CODEX-LOG.md, work continues.
- OWNER.SOURCE: explicit source/clock/count/parent events for SC, RED, GLUE, Hroot and compact native proposals; no silent canonical activation. Plain questions in CODEX-LOG.md, work continues.
### Waiting on COORD / ROOT-MERGE
- INFRA.MERGE and INFRA.REVIEW above are active queues; ready packages and diagnostics are not yet all published/released.

## CORE-SHAPE index (CORE-SHAPE-GATE-1, 2026-11-11 19:14 PST)
Hourly step (after the signed-store ingest): rebuild the signed-shape index the G0 check core_shape_change reads, on the hub (28 s, read-only on the store):
  python3 -I <main checkout>/tools/die_plan/core_shape.py build-index ~/coord/autopilot/core_shape_index.json.new --main-tree <tree holding main's *signoff.json, pins.json, config.mk> && mv ~/coord/autopilot/core_shape_index.json.new ~/coord/autopilot/core_shape_index.json
Die G0 runs add --core-shape-index ~/coord/autopilot/core_shape_index.json (opt-in; exact module re-shape = ERROR, base-name variant family only = WARN). Needs ROOT-MERGE-59 of claude/core-shape-gate-1.
