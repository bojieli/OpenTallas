# S81-KITS-1 (notes from PATH-S81, die plan/clock owner 12.9a)

## [PATH-S81-PD7 2026-10-27 02:49 PDT] HOLD list: band core-shift types (partition clock tap + core-entry xy move rigidly with the cores; islands core-relative unchanged)
- Die clock mesh rebuild = die-top only: mesh stubs drive the EXISTING PD5 partition/core clock entries; no entry moves for the mesh. Keep kitting every PD5 type EXCEPT these:
- HOLD (band shift c, 7 types, ruling-accepted path): col_h10_r1__t1 (12 inst, +8.64 x), dsdv_slice_c1x_C__t5_phy1026_s_4N_C, svc_hi_dsdv_svc_pvso_entry__t1_phy1026_svc_5, svc_hi_dsdv_svc_pvso_entry__t2 (svc_11), svc_hi_dsdv_svc_rs__t2_phy1026_svc_3, svc_hi_dsdv_svc_rs__t4 (svc_9), svc_hi_dsdv_svc_rs__t6_phy1026_svc_15.
- HOLD (band shift d, +3 types, also FT stations re-sited by ft_nudge): gunit__t1_phy1026_gunit, svc_lo_dsdv_svc_rs_w__t1_phy1026_svc_0, svc_hi_dsdv_svc_rs__t3_phy1026_svc_7.
- MERGED frame type (PD6, accepted): fW5_p1_b1/fW5_p2_b1/fE5_p1_b1 -> col_h9_r1__t1_pd5_b1_ew (kit once).
- Shift vectors + ledgers: claude/path-s81-pd7-1026 results/path_s81_pd7_1026/bands/{shift_base_d.json,shift_ledger_d.json,ft_nudge_ledger.json}.

## [PATH-S81-PD8 2026-10-27 03:36 PDT] RELEASE: band plan d ADOPTED (storage-band 8 -> 1, G0 13 = PD5 set; composed sha 34a2d168, claude/path-s81-pd8-1027@f30fc4babc)
- The HOLD list above (10 band core-shift types: 7 of c + gunit__t1_phy1026_gunit, svc_lo_dsdv_svc_rs_w__t1_phy1026_svc_0, svc_hi_dsdv_svc_rs__t3_phy1026_svc_7) is RELEASED. Kit them from intel1:/srv/opentallas-scratch2/claude/path-s81-pd7-1026/d (src/die_plan_pd7_composed.json, kit/), vectors in shift_ledger_d.json + ft_nudge_ledger.json.
- Caveat: the die mesh is not kit-neutral for every type. Without off_core_resite, 420 clock cells fell in hard cores. With it (PD8 md3), only bk_sel is still hit: 2 mesh drivers + 1 leg repeater in u_tx / u_sel.g_q[0,2].u_q. If S81-KITS kits bk_sel now, it may need a redo when the bk_sel islands are decided. All other types: no in-core clock island from the mesh.
