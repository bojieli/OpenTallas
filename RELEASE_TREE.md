# OpenTallas release tree (pending only; coordinator update 2026-11-01 18:00 PST)

2026-11-21 03:55 PST: see SIGN-RATE. up 1: any 493 (was 492), current 408 (was 407), flat 23:05-03:37 then QC slw_sc_v1__cl63e5a7a2 signed and exported (record 5f0e1ef62288): QC types 34/125. New sign-offs this hour: QC 1 (slw_sc_v1__cl63e5a7a2); S81, HEAD, KV, HBM none. Defer re-sign 19 (hbm 1, head 7, qc 10, s81 1), retired-plan 66. Per-die types S81 44/394 (cores 62/62), HEAD 25/26, QC 34/125, KV 6/56, HBM 4/84 parked. Codex 02:18-03:32 handback read (J6 C1n fallback passed bind/LATCHECK/G0/PRE, C3g/C3i have 27 new G0 findings each; QC b12 strict bind; HEAD r16 host_n/host_e/sdr2d GRT active; KV D26 portable bind). Detail route last 3 h: 46 distinct builds, 42 running DRT, 11 finished (sle_sc_v2/v3 among them); post-hook TT>=-42 and hold>=0: none; closest slw_su_l1__clcc9d0155 (TT +9.8, hold -112) and slw_su_l1__cla2a78701 (-9.6/-14.8, hold -123); every build has hold -62 to -178 pre-route, so hold repair in route decides. Scratch: intel1 scratch2 recovered to 189 GB free (not runaway); epyc9 scratch2 169 GB free at 98%, Codex excluded E9 from new admissions (dc77157231e), owner question open on the 4d15h KV peer proof container.
2026-11-20 01:1x PST CLOSURE PLAN (owner decisions on FABLE-CONVERGE-0215): ROM/name inheritance; daily plan event per die; representatives first. Yes to decisions 1, 2, 3, 4, 5, 6, 8; no to 7. Decision 4 (superset pinouts) is now YES (owner, about 01:1x PST) and FABLE-SUPERSET-0415 leads (lanes/FABLE-CONVERGE-0215.md). OWNER 11-20 ~02:xx PST: 833 ps is the fixed target, with no signing above it. Fix hold structurally, never by changing the clock. Fix setup misses with more pipeline stages.
Plans 11:36: count 152 flat (S81 50/58 + 4/205 types, HEAD 4/4 + 12/25, QC 16/19, KV 26/32, HBM 40/103). Merged I118-I126 since 10:40: QC coll_core fold + ring ff class (tag e-qc), KV PV taps (tag b-kv), HEAD l48ue (tag a-head), wave prune + resume fixes. 9 core gaps from CORE-FORMS-2 all owned. intel2 scratch2 142 after 49 GB move.

<!-- BREAKDOWN BEGIN -->
## FAILURES · unsigned cores and types by class (auto, 2026-11-21 04:09 PST)
count_hourly: signed any plan 493 | current plan 409 | deferred re-sign 18 (hbm 1, head 7, qc 9, s81 1) | retired-plan 66 (head 1, kv 12, qc 29, s81 24)
- [ ] FAIL.S81.CORES 62/62 signed · open: none
- [ ] FAIL.S81.TYPES 44/394 signed · kit rows: held by die owner (plan event pending) 275 (bk_sel__t2, +274) · running 51 · cancelled (superseded) 24 (col_h10_r0_p1__t1__cl574cc59d__pv67036687, +23) · other flow error 1 (s81sl_leaf__t39)
- [ ] FAIL.HEAD.CORES 5/5 signed · open: none
- [ ] FAIL.HEAD.TYPES 25/26 signed · kit rows: running 1
- [ ] FAIL.QC.CORES 70/70 signed · open: none
- [ ] FAIL.QC.TYPES 35/125 signed · kit rows: running 73 · held by die owner (plan event pending) 10 (cbf_q00__cl1b5a6458, +9) · cancelled (superseded) 6 (cbf_q01, +5) · running (lint advisory) 1 (sle_st_b_v1__pvc5a85fd4__pv7b7fafb4)
- [ ] FAIL.KV.CORES 68/69 signed · open: cancelled (superseded) 1 (qkd_pv_fin_s8_pin)
- [ ] FAIL.KV.TYPES 6/56 signed · kit rows: running 18 · held by die owner (plan event pending) 18 (kv3_hg, +17) · other flow error 7 (kv3_hgi_v3, +6) · cancelled (superseded) 3 (kv3_hgi_v2__cl2862d491, +2) · running (lint advisory) 2 (kv3_hgi_v4, +1) · bind stale vs plan (re-bind) 1 (kv3_pv_v8) · PDN-0006 1 (kv3_pc_v3)
- [ ] FAIL.HBM.CORES 90/118 signed · open: cancelled (superseded) 12 (hgi_sfu_opsa_group0, hgi_sfu_opsb_group, hnx_vms_bank_q0_faces__vecd4ae, +5) · running, no result 9 (hfd_coll_q2n2_vm_core, hfd_hgi_vms_glue_nw_t, hgi_coll_tkm_m_tp192__root, +6) · no kit-wave row 6 (accel_smh_pt_w, hfd_coll_q3_body_ctl, hgi_sfu_opsa_group1, +3) · shape: over cells/util/congestion 1 (hgi_dma_back_static_vp4_banks_cp)
- [ ] FAIL.HBM.TYPES 4/84 signed · kit rows: cancelled (superseded) 90 (NE_io, +89) · held by die owner (plan event pending) 22 (NE_iorly, +21)
### STALE · unsigned plan cores/types with no live job and no kit-wave row change >= 6 h: 106 current-event (+1 on a superseded plan block, not counted) (live check: ps/systemd/docker on all hosts, NOT SEEN: intel2; wave state: local copy 11-21 04:08; full list lanes/STALE.tsv)
- [ ] STALE.S81 1 (cores 0, types 1) · by owner: FAIL-S81-1 1
  - type iqf__t1 · ROUTE-HELD geom @ 2026-11-20 17:26 (10.7h) · owner FAIL-S81-1
- [ ] STALE.KV 2 (cores 1, types 1) · by owner: unowned 1, KIT-WAVE-1 1
  - core qkd_pv_fin_s8_pin · CANCELLED gen SUPERSEDED @ 2026-11-20 09:28 (18.7h) · owner unowned
  - type kv3_io_cor_v1 · FAIL route INFRA @ 2026-11-20 21:37 (6.5h) · owner KIT-WAVE-1
- [ ] STALE.HBM 104 (cores 27, types 77) · by owner: KIT-WAVE-1 77, unowned 11, HBM-CORES-B 6, HBM-CORES 5, DIE-HBM-98 3, AUTO-RESIGN 1, HBM-PLAN 1
  - core ot_hbm_accel_smh_pt_w · no kit-wave row · owner unowned
  - core ot_hbm_su_pg_lane1p_core · no kit-wave row · owner AUTO-RESIGN
  - core ot_hfd_coll_q3_body_ctl · no kit-wave row · owner HBM-CORES-B
  - core ot_hgi_sfu_opsa_group1 · no kit-wave row · owner HBM-CORES-B
  - core ot_pdie_serdes_rx_bm3_rest · no kit-wave row · owner unowned
  - core ot_wbq_sw · no kit-wave row · owner HBM-CORES-B
  - type q_mcb_nw · no kit-wave row · owner unowned
  - type NE_iorly · ROUTE-HELD geom @ 2026-11-13 03:26 (192.7h) · owner unowned
  - type NW_iorly · ROUTE-HELD geom @ 2026-11-13 03:26 (192.7h) · owner unowned
  - type PHY_NC · ROUTE-HELD geom @ 2026-11-13 03:27 (192.7h) · owner DIE-HBM-98
  - type vsN5 · ROUTE-HELD geom @ 2026-11-13 03:27 (192.7h) · owner KIT-WAVE-1
  - type vsN2 · ROUTE-HELD geom @ 2026-11-13 07:23 (188.8h) · owner KIT-WAVE-1
  - type PHY_NE · CANCELLED geom SUPERSEDED @ 2026-11-16 07:11 (117h) · owner DIE-HBM-98
  - core hnx_fused_lane_c · CANCELLED geom SUPERSEDED @ 2026-11-16 07:11 (117h) · owner unowned
  - core ot_hbm_sm_i8w_front · CANCELLED geom SUPERSEDED @ 2026-11-16 07:11 (117h) · owner unowned
  - core ot_hbm_sm_kv_line · CANCELLED geom SUPERSEDED @ 2026-11-16 07:11 (117h) · owner HBM-CORES-B
  - core ot_hbm_sm_pv_merge · CANCELLED geom SUPERSEDED @ 2026-11-16 07:11 (117h) · owner unowned
  - core ot_hbm_svc_vm_kshare_splitstrap__v8e478a · CANCELLED geom SUPERSEDED @ 2026-11-16 07:11 (117h) · owner KIT-WAVE-1
  - core ot_hfd_coll_q2n2_vm_core · CANCELLED geom SUPERSEDED @ 2026-11-16 07:11 (117h) · owner KIT-WAVE-1
  - core ot_hgi_sfu_programme_store_r10 · CANCELLED geom SUPERSEDED @ 2026-11-16 07:11 (117h) · owner KIT-WAVE-1
  - core ot_q2nf_rest · CANCELLED geom SUPERSEDED @ 2026-11-16 07:11 (117h) · owner HBM-CORES-B
  - type q_mcb_ne · CANCELLED geom SUPERSEDED @ 2026-11-16 07:11 (117h) · owner unowned
  - type q_spu0__physical_v1 · CANCELLED geom SUPERSEDED @ 2026-11-16 07:11 (117h) · owner KIT-WAVE-1
  - type vsN4 · CANCELLED geom SUPERSEDED @ 2026-11-16 07:11 (117h) · owner KIT-WAVE-1
  - type vsN6 · CANCELLED geom SUPERSEDED @ 2026-11-16 07:11 (117h) · owner KIT-WAVE-1
  - type NE_io · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_b002 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) row q_b002__physical_v1 · owner KIT-WAVE-1
  - type q_b002__physical_v1 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_b003__physical_v1 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_b011 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) row q_b011__physical_v1 · owner KIT-WAVE-1
  - type q_b011__physical_v1 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_b012 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) row q_b012__physical_v1 · owner KIT-WAVE-1
  - type q_b012__physical_v1 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_b013 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) row q_b013__physical_v1 · owner KIT-WAVE-1
  - type q_b013__physical_v1 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_b100__physical_v1 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_b101_nw · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_b102 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) row q_b102__physical_v1 · owner KIT-WAVE-1
  - type q_b102__physical_v1 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_b103 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) row q_b103__physical_v1 · owner KIT-WAVE-1
  - type q_b103__physical_v1 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_b110 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) row q_b110__physical_v1 · owner KIT-WAVE-1
  - type q_b110__physical_v1 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_b111 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) row q_b111__physical_v1 · owner KIT-WAVE-1
  - type q_b111__physical_v1 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_b112 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) row q_b112__physical_v1 · owner KIT-WAVE-1
  - type q_b112__physical_v1 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_b113 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) row q_b113__physical_v1 · owner KIT-WAVE-1
  - type q_b113__physical_v1 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_hub_ne · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_hub_nw · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner HBM-PLAN
  - type q_spb0__physical_v1 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_spb2__physical_v1 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_spt0 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) row q_spt0__physical_v1 · owner KIT-WAVE-1
  - type q_spt0__physical_v1 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_spt1 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_su00 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) row q_su00__physical_v1 · owner KIT-WAVE-1
  - type q_su00__physical_v1 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_su01 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) row q_su01__physical_v1 · owner KIT-WAVE-1
  - type q_su01__physical_v1 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_su10 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) row q_su10__physical_v1 · owner KIT-WAVE-1
  - type q_su10__physical_v1 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_su20__physical_v1 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_su21 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) row q_su21__physical_v1 · owner KIT-WAVE-1
  - type q_su21__physical_v1 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type q_su31 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) row q_su31__physical_v1 · owner KIT-WAVE-1
  - type q_su31__physical_v1 · LINT-ADVISORY prelint LINT @ 2026-11-16 13:25 (110.7h) · owner KIT-WAVE-1
  - type NW_io · CANCELLED place SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner KIT-WAVE-1
  - type PHY_NW · CANCELLED place SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner DIE-HBM-98
  - core hfd_hgi_vms_glue_nw_t · CANCELLED gen SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner KIT-WAVE-1
  - core hnx_vms_bank_q0_faces__vecd4ae#270x403.92/430f68dee83dc012 · CANCELLED gen SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner HBM-CORES
  - core hnx_vms_bank_q0_faces__vecd4ae#270x403.92/6d132375c20a740b · CANCELLED gen SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner HBM-CORES
  - core hnx_vms_bank_q0_faces__vecd4ae#270x403.92/b7314a95f9eb7d23 · CANCELLED gen SUPERSEDED @ 2026-11-18 04:25 (71.7h) row hnx_vms_bank_q0_faces__vecd4ae__v796f3e53bd3f · owner HBM-CORES
  - core hnx_vms_bank_q0_faces__vecd4ae#270x403.92/b95ff4f969a6c0ba · CANCELLED gen SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner HBM-CORES
  - core hnx_vms_bank_q0_faces__vecd4ae#270x403.92/d4e89c75b4a66b6e · CANCELLED gen SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner HBM-CORES
  - core ot_hbm_idx_topk_link_static · CANCELLED place SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner KIT-WAVE-1
  - core ot_hbm_svc_vm_kshare_splitstrap__v700685 · CANCELLED place SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner KIT-WAVE-1
  - core ot_hgi_coll_tkm_m_tp192__root · CANCELLED gen SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner KIT-WAVE-1
  - core ot_hgi_dma_back_static_vp4_banks_cp · CANCELLED gen SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner KIT-WAVE-1
  - core ot_hgi_sfu_opsa_group0 · CANCELLED gen SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner unowned
  - core ot_hgi_sfu_opsb_group · CANCELLED gen SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner HBM-CORES-B
  - core ot_svgr_top · CANCELLED place SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner unowned
  - type q_b000 · CANCELLED place SUPERSEDED @ 2026-11-18 04:25 (71.7h) row q_b000__physical_v1 · owner KIT-WAVE-1
  - type q_b000__physical_v1 · CANCELLED place SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner KIT-WAVE-1
  - type q_b001 · CANCELLED place SUPERSEDED @ 2026-11-18 04:25 (71.7h) row q_b001__physical_v1 · owner KIT-WAVE-1
  - type q_b001__physical_v1 · CANCELLED place SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner KIT-WAVE-1
  - type q_b003 · CANCELLED kit_topology SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner KIT-WAVE-1
  - type q_b010 · CANCELLED place SUPERSEDED @ 2026-11-18 04:25 (71.7h) row q_b010__physical_v1 · owner KIT-WAVE-1
  - type q_b010__physical_v1 · CANCELLED place SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner KIT-WAVE-1
  - type q_b100 · CANCELLED place SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner KIT-WAVE-1
  - type q_b101 · CANCELLED place SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner KIT-WAVE-1
  - type q_sm0 · CANCELLED place SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner KIT-WAVE-1
  - type q_sm1 · CANCELLED place SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner KIT-WAVE-1
  - type q_sm2 · CANCELLED place SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner KIT-WAVE-1
  - type q_sm3 · CANCELLED place SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner KIT-WAVE-1
  - type q_spb0 · CANCELLED kit_rtl SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner KIT-WAVE-1
  - type q_spb2 · CANCELLED geom SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner KIT-WAVE-1
  - type q_spu0 · CANCELLED place SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner KIT-WAVE-1
  - type q_spu1 · CANCELLED geom SUPERSEDED @ 2026-11-18 04:25 (71.7h) row q_spu1__physical_v1 · owner KIT-WAVE-1
  - type q_spu1__physical_v1 · CANCELLED geom SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner KIT-WAVE-1
  - type q_su11 · CANCELLED geom SUPERSEDED @ 2026-11-18 04:25 (71.7h) row q_su11__physical_v1 · owner KIT-WAVE-1
  - type q_su11__physical_v1 · CANCELLED geom SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner KIT-WAVE-1
  - type q_su20 · CANCELLED place SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner KIT-WAVE-1
  - type vsN0 · CANCELLED kit_rtl SUPERSEDED @ 2026-11-18 04:25 (71.7h) · owner KIT-WAVE-1
### TOOLS-LAG · die tool fixes missing from the pinned trees
- TOOLS-LAG hbm 3149 commits / missing r407 r409 r421 r422 r428 r431 r433 r435 r454 r457 r458 r459 r467 r468 r471 r473 r474 r476 r477 r478 r479 r481 r482 r483 r484 r488 r489 r490 r491 r493 r494 r495 r496 r497 r498 r503 r507 r546 r547 r548 +141 more
- TOOLS-LAG qwen_compute 159 commits / missing r708
- TOOLS-LAG qwen_kvsys 567 commits / missing r708
- TOOLS-LAG s81 unmeasured (git rev-list --count: fatal: bad revision 'j5tree..main')
- TOOLS-LAG s81_head 105 commits / missing r708
### TAP-INSERTION · measured per-tap insertion after CTS (advisory)
- TAP-INSERTION qwen_compute: 1909 taps in 20 types, 41 over 1650 sinks; insertion max 493 ps (p50 269, p90 286), skew max 137 ps; oversized taps: ins max 299 ps, skew max 57 ps
- TAP-INSERTION qwen_kvsys: 111 taps in 2 types, 1 over 1650 sinks; insertion max 333 ps (p50 268, p90 297), skew max 87 ps; oversized taps: ins max 273 ps, skew max 26 ps
- TAP-INSERTION s81: 2444 taps in 42 types, 112 over 1650 sinks; insertion max 852 ps (p50 464, p90 496), skew max 347 ps; oversized taps: ins max 815 ps, skew max 301 ps
- TAP-INSERTION s81_head: 154 taps in 8 types, 0 over 1650 sinks; insertion max 501 ps (p50 464, p90 481), skew max 82 ps; oversized taps: ins max - ps, skew max - ps
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
